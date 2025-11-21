///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 13 November 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICSRU
covergroup ZicsrU_uprivinst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // "ZicsrU uprivinst"

    // building blocks for the main coverpoints
    privinstrs: coverpoint ins.current.insn  {
        bins ecall  = {32'h00000073};
        bins ebreak = {32'h00100073};
    }
    mret: coverpoint ins.current.insn  {
        bins mret   = {32'h30200073};
    }
    sret: coverpoint ins.current.insn  {
        bins sret   = {32'h10200073};
    }

    // main coverpoints
    cp_uprivinst:  cross privinstrs, priv_mode_u;
    cp_mret:       cross mret, priv_mode_u; // should trap
    cp_sret:       cross sret, priv_mode_u; // should trap
endgroup

function void zicsru_sample(int hart, int issue, ins_t ins);
    ZicsrU_uprivinst_cg.sample(ins);
endfunction
