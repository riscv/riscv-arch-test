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
// This file contains all coverpoint definitions that are identical
// across all Zicfilp privilege-mode coverage files.
///////////////////////////////////////////////


    indirect_ct: coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }
    `ifdef COVER_ZCA
        indirect_ct_c: coverpoint ins.current.insn[15:0] {
            wildcard bins c_jr   = {C_JR};
            wildcard bins c_jalr = {C_JALR};
        }
    `endif
     indirect_ct_prev: coverpoint ins.prev.insn {
        wildcard bins jalr = {JALR};
    }
    `ifdef COVER_ZCA
        indirect_ct_prev_c: coverpoint ins.prev.insn[15:0] {
            wildcard bins c_jr   = {C_JR};
            wildcard bins c_jalr = {C_JALR};
        }
    `endif
    rs1_all_prev: coverpoint ins.prev.insn[19:15] {
        bins all_except_x0[] = {[5'd1:5'd31]};
    }
    `ifdef COVER_ZCA
        rs1_all_prev_c: coverpoint ins.prev.insn[11:7] {
            bins all_except_x0[] = {[5'd1:5'd31]};
        }
    `endif
    lpad_lpl_zero: coverpoint ins.current.insn {
        wildcard bins lpad_zero = {32'b00000000000000000000_00000_0010111};
    }
    lpad_lpl_nonzero: coverpoint (
        ins.current.insn[11:0] == 12'b000000010111 &&
        ins.current.insn[31:12] != 20'h0) {
        bins lpl_nonzero = {1};
   }
    not_lpad: coverpoint (ins.current.insn[11:0] != 12'b000000010111) { }
    lpad_dest: coverpoint (ins.current.insn[11:0] == 12'b000000010111) { }
    rs1_all: coverpoint ins.current.insn[19:15] {
        bins all_except_x0[] = {[5'd1:5'd31]};
    }
    `ifdef COVER_ZCA
        rs1_all_c: coverpoint ins.current.insn[11:7] {
            bins all_except_x0[] = {[5'd1:5'd31]};
        }
    `endif
    rs1_link: coverpoint ins.current.insn[19:15] {
        bins x1 = {5'd1};
        bins x5 = {5'd5};
        bins x7 = {5'd7};
    }
    `ifdef COVER_ZCA
        rs1_link_c: coverpoint ins.current.insn[11:7] {
            bins x1 = {5'd1};
            bins x5 = {5'd5};
            bins x7 = {5'd7};
        }
    `endif
    x7_label: coverpoint  ins.prev.x_wdata[7][31:12] {
        bins label_zero    = {20'h0};
        bins label_nonzero = {[20'h1:20'hFFFFF]};
    }
    lpl_match: coverpoint (ins.current.imm[31:12] == ins.prev.x_wdata[7][31:12]) { }
    lpad_scenario: coverpoint {
        ins.current.insn[11:0] == 12'b000000010111,
        (ins.current.imm[31:12] == ins.prev.x_wdata[7][31:12]),
        (ins.prev.x_wdata[7][31:12] == 20'h0)
    } {
        wildcard bins sc1_match     = {3'b1_1_0};
        wildcard bins sc2_mismatch  = {3'b1_0_0};
        wildcard bins sc3_not_lpad  = {3'b0_?_?};
        wildcard bins sc4_lpl_zero_no_match_required = {3'b1_0_1};
    }
    sw_check_exc: coverpoint ins.current.csr[12'h342] {
        bins cause_18 = {18};
    }
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        pc_fault_addr: coverpoint ins.current.pc_rdata {
            bins fault_addr = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }
    `endif
