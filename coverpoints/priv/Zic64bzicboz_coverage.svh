///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for RVA23U64 profile - Zic64bzicboz extension
///////////////////////////////////////////////

`define COVER_ZIC64BZICBOZ

covergroup Zic64bzicboz_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `ifdef XLEN64
    `ifdef ZICBOZ_SUPPORTED

    cbo_zero: coverpoint ins.current.insn {
        wildcard bins cbo_zero = {CBO_ZERO};
    }

    cbo_zero_offset: coverpoint ins.current.rs1_val[6:0] {
        bins offset_0  = {7'd0};
        bins offset_4  = {7'd4};
        bins offset_8  = {7'd8};
        bins offset_12 = {7'd12};
        bins offset_16 = {7'd16};
        bins offset_20 = {7'd20};
        bins offset_24 = {7'd24};
        bins offset_28 = {7'd28};
        bins offset_32 = {7'd32};
        bins offset_36 = {7'd36};
        bins offset_40 = {7'd40};
        bins offset_44 = {7'd44};
        bins offset_48 = {7'd48};
        bins offset_52 = {7'd52};
        bins offset_56 = {7'd56};
        bins offset_60 = {7'd60};
        bins offset_64 = {7'd64};
    }

    cp_zic64bzicboz: cross cbo_zero, cbo_zero_offset, priv_mode_u;

    `endif
    `endif

endgroup

function void zic64bzicboz_sample(int hart, int issue, ins_t ins);
    Zic64bzicboz_cg.sample(ins);
endfunction
