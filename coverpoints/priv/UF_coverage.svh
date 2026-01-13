///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: David_Harris@hmc.edu 12 January 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_UF

covergroup UF_ufcsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrname : coverpoint ins.current.insn[31:20] {
        bins fcsr      = {12'h003};
        bins fflags    = {12'h001};
        bins frm       = {12'h002};
    }

    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`XLEN-1] };
    }

    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }

    csraccesses : coverpoint {ins.current.rs1_val, ins.current.insn[14:12]} iff (ins.current.insn[6:0] == 7'b1110011) {
        `ifdef XLEN64
            bins csrrc_all = {67'b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111_011};
            bins csrrw0    = {67'b00000000_00000000_00000000_00000000_00000000_00000000_00000000_00000000_001};
            bins csrrw1    = {67'b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111_001};
            bins csrrs_all = {67'b11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111_010};
            bins csrr      = {67'b00000000_00000000_00000000_00000000_00000000_00000000_00000000_00000000_010};
        `else
            bins csrrc_all = {35'b11111111_11111111_11111111_11111111_011}; // csrc all ones
            bins csrrw0    = {35'b00000000_00000000_00000000_00000000_001}; // csrw all zeros
            bins csrrw1    = {35'b11111111_11111111_11111111_11111111_001}; // csrw all ones
            bins csrrs_all = {35'b11111111_11111111_11111111_11111111_010}; // csrs all ones
            bins csrr      = {35'b00000000_00000000_00000000_00000000_010}; // csrr
        `endif
    }

    cp_ufcsr_access:           cross priv_mode_s, csrname, csraccesses;
    cp_ufcsrwalk:              cross priv_mode_s, csrname, csrop, walking_ones;
    cp_ucsr_from_m:            cross priv_mode_m, csrname, csraccesses;
endgroup

function void uf_sample(int hart, int issue, ins_t ins);
    UF_ufcsr_cg.sample(ins);
endfunction
