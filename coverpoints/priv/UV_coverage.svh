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
`define COVER_UV

covergroup UV_uvcsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrname : coverpoint ins.current.insn[31:20] {
        bins vstart = {12'h008};
        bins vxsat  = {12'h009};
        bins vxrm   = {12'h00A};
        bins vcsr   = {12'h00F};
        bins vl     = {12'hC20};
        bins vtype  = {12'hC21};
        bins vlenb  = {12'hC22};
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

    cp_uvcsr_access:           cross priv_mode_u, csrname, csraccesses;
    cp_uvcsrwalk:              cross priv_mode_u, csrname, csrop, walking_ones;
    cp_ucsr_from_m:            cross priv_mode_m, csrname, csraccesses;
endgroup

function void uv_sample(int hart, int issue, ins_t ins);
    UV_uvcsr_cg.sample(ins);
endfunction
