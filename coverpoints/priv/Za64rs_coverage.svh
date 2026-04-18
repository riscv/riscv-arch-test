///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: ammarahwakeel9@gmail.com (UET LAHORE)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for RVA23U64 profile - Za64rs extension
///////////////////////////////////////////////


`define COVER_ZA64RS

covergroup Za64rs_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    `ifdef XLEN64

    lr_w_instr: coverpoint ins.current.insn {
        wildcard bins lr_w = {LR_W};
    }

    sc_w_instr: coverpoint ins.current.insn {
        wildcard bins sc_w = {SC_W};
    }

    lr_w_base_aligned: coverpoint ins.current.rs1_val[5:0] {
        bins aligned_64 = {6'd0};
    }

    sc_offset_success: coverpoint ins.current.rs1_val[6:0] {
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
    }

    sc_offset_fail: coverpoint ins.current.rs1_val[6:0] {
        bins offset_64 = {7'd64};
    }

    sc_fail: coverpoint ins.current.rd_val {
        bins fail = {[1:$]};
    }

    cp_za64rs_lr:      cross priv_mode_u, lr_w_instr, lr_w_base_aligned;
    cp_za64rs_success: cross priv_mode_u, sc_w_instr, sc_offset_success;
    cp_za64rs_fail:    cross priv_mode_u, sc_w_instr, sc_offset_fail, sc_fail;

    `endif

endgroup

function void za64rs_sample(int hart, int issue, ins_t ins);
    Za64rs_cg.sample(ins);
endfunction
