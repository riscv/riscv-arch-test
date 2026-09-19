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
// defines its own mode-specific coverpoints (xLPE, ELP, trap CSRs) and crosses.
///////////////////////////////////////////////

// An indirect call/jump sets ELP=LP_EXPECTED (when xLPE=1) unless rs1 is x1, x5, or x7.
// rs1=x0 is excluded from the compressed form because that encoding is c.ebreak.
`ifndef ZICFILP_LP_JALR
    `define ZICFILP_LP_JALR(INSN)  (((INSN) ==? JALR) && !((INSN[19:15]) inside {5'd1, 5'd5, 5'd7}))
    `define ZICFILP_LP_CJUMP(INSN) ((((INSN) ==? C_JR) || ((INSN) ==? C_JALR)) && !((INSN[11:7]) inside {5'd0, 5'd1, 5'd5, 5'd7}))
    `ifdef ZCA_SUPPORTED
        `define ZICFILP_LP_BRANCH(INSN) (`ZICFILP_LP_JALR(INSN) || `ZICFILP_LP_CJUMP(INSN))
    `else
        `define ZICFILP_LP_BRANCH(INSN) `ZICFILP_LP_JALR(INSN)
    `endif
`endif

    // Previous instruction was an indirect call/jump, so the current instruction is its target
    indirect_ct_prev: coverpoint ins.prev.insn {
        wildcard bins jalr = {JALR};
    }
    rs1_all_prev: coverpoint ins.prev.insn[19:15] {
        bins all_except_x0[] = {[5'd1:5'd31]};
    }
    rs1_link_prev: coverpoint ins.prev.insn[19:15] {
        bins x1 = {5'd1};
        bins x5 = {5'd5};
        bins x7 = {5'd7};
    }
    `ifdef ZCA_SUPPORTED
        indirect_ct_prev_c: coverpoint ins.prev.insn {
            wildcard bins c_jr   = {C_JR};
            wildcard bins c_jalr = {C_JALR};
        }
        rs1_all_prev_c: coverpoint ins.prev.insn[11:7] {
            bins all_except_x0[] = {[5'd1:5'd31]};
        }
        rs1_link_prev_c: coverpoint ins.prev.insn[11:7] {
            bins x1 = {5'd1};
            bins x5 = {5'd5};
            bins x7 = {5'd7};
        }
    `endif

    // Current instruction
    lpad_dest: coverpoint (ins.current.insn ==? LPAD) {
        bins not_lpad = {1'b0};
        bins lpad     = {1'b1};
    }
    // A legal instruction other than LPAD, or an illegal instruction (the software-check exception has priority)
    not_lpad: coverpoint {(ins.current.insn ==? LPAD), (ins.current.insn == 32'hFFFFFFFF)} {
        bins legal_instruction   = {2'b00};
        bins illegal_instruction = {2'b01};
    }
    lpad_lpl_zero: coverpoint ins.current.insn {
        bins lpad_zero = {32'h00000017};
    }
    lpad_lpl_nonzero: coverpoint ((ins.current.insn ==? LPAD) && (ins.current.insn[31:12] != 20'h0)) {
        bins lpl_nonzero = {1'b1};
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

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Current instruction is an ELP-setting JALR whose target raises an instruction access fault
        lp_jalr_to_fault_addr: coverpoint (`ZICFILP_LP_JALR(ins.current.insn) &&
                                           ((ins.current.imm + ins.current.rs1_val) == `RVMODEL_ACCESS_FAULT_ADDRESS)) {
            bins lp_jalr = {1'b1};
        }
    `endif
