///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Eman Nasar  email:fatehulnasareman@gmail.com (UET, May 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
// Description: Zicfilp Shared Coverpoints
//
// This file contains the coverpoint definitions that do not depend on the
// privilege mode. Each Zicfilp privilege-mode coverage file includes it and
// defines its own mode-specific coverpoints (xLPE, trap CSRs) and crosses.
// Crosses describe the conditions a test sets up; the expected outcomes
// (exceptions, xtval, ELP) are checked by the signature.
///////////////////////////////////////////////

// An indirect call/jump sets ELP=LP_EXPECTED (when xLPE=1) unless rs1 is x1, x5, or x7.
// TD is a trace record (ins.prev or ins.current). ZICFILP_RS1 is its decoded rs1 for jalr, c.jr and c.jalr,
// and x0 for any other instruction. c.ebreak shares the c.jalr encoding with rs1=x0 and has no rs1 operand.
`ifndef ZICFILP_LP_JALR
    `define ZICFILP_INDIRECT(TD)   ((TD.insn ==? JALR) || (TD.insn ==? C_JR) || (TD.insn ==? C_JALR))
    `define ZICFILP_RS1(TD)        ((`ZICFILP_INDIRECT(TD) && TD.has_rs1) ? ins.get_gpr_reg(TD.rs1) : x0)
    `define ZICFILP_RS1_LINK(TD)   ((`ZICFILP_RS1(TD) == x1) || (`ZICFILP_RS1(TD) == x5) || (`ZICFILP_RS1(TD) == x7))
    `define ZICFILP_LP_JALR(TD)    ((TD.insn ==? JALR) && !`ZICFILP_RS1_LINK(TD))
    `define ZICFILP_LP_CJUMP(TD)   (((TD.insn ==? C_JR) || (TD.insn ==? C_JALR)) && (`ZICFILP_RS1(TD) != x0) && !`ZICFILP_RS1_LINK(TD))
    `ifdef ZCA_SUPPORTED
        `define ZICFILP_LP_BRANCH(TD) (`ZICFILP_LP_JALR(TD) || `ZICFILP_LP_CJUMP(TD))
    `else
        `define ZICFILP_LP_BRANCH(TD) `ZICFILP_LP_JALR(TD)
    `endif
`endif

    // Previous instruction was an indirect call/jump, so the current instruction is its target
    indirect_ct_prev: coverpoint ins.prev.insn {
        wildcard bins jalr = {JALR};
    }
    rs1_all_prev: coverpoint `ZICFILP_RS1(ins.prev) {
        ignore_bins x0 = {x0};
    }
    rs1_link_prev: coverpoint `ZICFILP_RS1(ins.prev) {
        bins x1 = {x1};
        bins x5 = {x5};
        bins x7 = {x7};
    }
    `ifdef ZCA_SUPPORTED
        indirect_ct_prev_c: coverpoint ins.prev.insn {
            wildcard bins c_jr   = {C_JR};
            wildcard bins c_jalr = {C_JALR};
        }
        rs1_all_prev_c: coverpoint `ZICFILP_RS1(ins.prev) {
            ignore_bins x0 = {x0};
        }
        rs1_link_prev_c: coverpoint `ZICFILP_RS1(ins.prev) {
            bins x1 = {x1};
            bins x5 = {x5};
            bins x7 = {x7};
        }
    `endif

    // Previous instruction was an Indirect_CT through a register other than x1/x5/x7:
    // with xLPE=1 the current instruction executes with ELP=LP_EXPECTED
    lp_branch_prev: coverpoint (
        `ZICFILP_LP_JALR(ins.prev)                                ? 2'd1 :
        (`ZICFILP_LP_CJUMP(ins.prev) && (ins.prev.insn ==? C_JR)) ? 2'd2 :
        `ZICFILP_LP_CJUMP(ins.prev)                               ? 2'd3 : 2'd0) {
        bins jalr = {2'd1};
        `ifdef ZCA_SUPPORTED
            bins c_jr   = {2'd2};
            bins c_jalr = {2'd3};
        `endif
    }

    // Current instruction
    lpad_dest: coverpoint (ins.current.insn ==? LPAD) {
        bins not_lpad = {1'b0};
        bins lpad     = {1'b1};
    }
    not_lpad: coverpoint (ins.current.insn ==? LPAD) {
        bins not_lpad = {1'b0};
    }
    lpad_lpl_zero: coverpoint ins.current.insn {
        bins lpad_zero = {32'h00000017};
    }
    lpad_lpl_nonzero: coverpoint ((ins.current.insn ==? LPAD) && (ins.current.insn[31:12] != 20'h0)) {
        bins lpl_nonzero = {1'b1};
    }
    // An LPAD that passes the label check: LPL=0, or LPL equal to x7[31:12]
    lpad_valid: coverpoint {(ins.current.insn ==? LPAD), (ins.current.insn[31:12] == 20'h0),
                            (ins.current.insn[31:12] == ins.prev.x_wdata[7][31:12])} {
        wildcard bins lpl_zero  = {3'b1_1_?};
        wildcard bins lpl_match = {3'b1_0_1};
    }
    pc_aligned: coverpoint ins.current.pc_rdata[1:0] {
        bins aligned = {2'b00};
    }
    `ifdef ZCA_SUPPORTED
        pc_misaligned: coverpoint ins.current.pc_rdata[1:0] {
            bins misaligned = {2'b10};
        }
    `endif

    // Previous instruction was not an ELP-setting Indirect_CT, so the current instruction executes with ELP=NO_LP_EXPECTED
    no_lp_branch_prev: coverpoint `ZICFILP_LP_BRANCH(ins.prev) {
        bins no_lp_expected = {1'b0};
    }
    // An LPAD that would fail the landing pad check if ELP were LP_EXPECTED:
    // {is LPAD, LPL != 0 and LPL != x7[31:12], pc[1:0] == 2}
    lpad_nop_case: coverpoint {(ins.current.insn ==? LPAD),
                               ((ins.current.insn[31:12] != 20'h0) &&
                                (ins.current.insn[31:12] != ins.prev.x_wdata[7][31:12])),
                               (ins.current.pc_rdata[1:0] == 2'b10)} {
        bins lpl_mismatch = {3'b1_1_0};
        `ifdef ZCA_SUPPORTED
            bins misaligned = {3'b1_0_1};
        `endif
    }

    // Expected landing pad label in x7[31:12] and the LPL encoded in the LPAD instruction
    x7_label: coverpoint ins.prev.x_wdata[7][31:12] {
        bins label_zero    = {20'h0};
        bins label_nonzero = {[20'h1:20'hFFFFF]};
    }
    lpl_match: coverpoint (ins.current.insn[31:12] == ins.prev.x_wdata[7][31:12]) {
        bins mismatch = {1'b0};
        bins match    = {1'b1};
    }
    // Only x7[31:12] takes part in the label check. Crossing a nonzero x7[11:0] into the label
    // match and mismatch cases keeps a DUT that compares the whole register, or x7[31:0]
    // against {LPL,12'b0}, from passing.
    x7_low_bits: coverpoint (ins.prev.x_wdata[7][11:0] != 12'h0) {
        bins nonzero = {1'b1};
    }
    // {is LPAD, LPL != 0, LPL == x7[31:12], x7[31:12] == 0}
    lpad_scenario: coverpoint {
        (ins.current.insn ==? LPAD),
        (ins.current.insn[31:12] != 20'h0),
        (ins.current.insn[31:12] == ins.prev.x_wdata[7][31:12]),
        (ins.prev.x_wdata[7][31:12] == 20'h0)
    } {
        wildcard bins sc1_match            = {4'b1_1_1_0};
        wildcard bins sc2_mismatch         = {4'b1_1_0_0};
        wildcard bins sc3_not_lpad         = {4'b0_?_?_?};
        wildcard bins sc4_x7_label_zero    = {4'b1_1_0_1};
    }

    // Exception priority at the target of an ELP-setting Indirect_CT:
    // an instruction access fault (logged with the JALR, which has no target record) or an illegal instruction
    priority_case: coverpoint {
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
            (`ZICFILP_LP_JALR(ins.current) &&
             ((ins.current.imm + ins.current.rs1_val) == `RVMODEL_ACCESS_FAULT_ADDRESS)),
        `else
            1'b0,
        `endif
        (`ZICFILP_LP_BRANCH(ins.prev) && (ins.current.insn == 32'hFFFFFFFF))
    } {
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
            bins instr_access_fault = {2'b10};
        `endif
        bins illegal_instruction = {2'b01};
    }

    // Trap entry: a software-check exception at the target of an ELP-setting Indirect_CT (ELP=LP_EXPECTED),
    // or an ecall that no such Indirect_CT precedes (ELP=NO_LP_EXPECTED)
    trap_case: coverpoint {(`ZICFILP_LP_BRANCH(ins.prev) && !(ins.current.insn ==? LPAD)),
                           (!`ZICFILP_LP_BRANCH(ins.prev) && (ins.current.insn == ECALL))} {
        bins lp_expected_not_lpad = {2'b10};
        bins no_lp_expected_ecall = {2'b01};
    }
