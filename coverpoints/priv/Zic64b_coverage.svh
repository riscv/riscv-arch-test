///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written:  Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for the Zic64b 64-byte cache block
///////////////////////////////////////////////

`define COVER_ZIC64B

covergroup Zic64b_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    cbo_zero: coverpoint ins.current.insn {
        wildcard bins cbo_zero = {CBO_ZERO};
    }
    // Offsets from a 128-byte-aligned base: the block, one unaligned byte, and the next block.
    cbo_zero_offset: coverpoint ins.current.rs1_val[6:0] {
        bins offset_0 = {7'd0};
        bins offset_1 = {7'd1};
        bins offset_63 = {7'd63};
        bins offset_64 = {7'd64};
    }
    // Offset of rs1 inside its 64-byte block. Used at a page or PMP boundary.
    block_offset: coverpoint ins.current.rs1_val[5:0] {
        bins off_0 = {6'd0};
        bins off_63 = {6'd63};
    }

    cp_zic64b: cross cbo_zero, cbo_zero_offset iff (ins.trap == 0);
    cp_zic64b_sv_ok: cross cbo_zero, block_offset, priv_mode_s iff (ins.trap == 0);
    cp_zic64b_sv_fault: cross cbo_zero, block_offset, priv_mode_s iff (ins.trap != 0);
    cp_zic64b_pmp_fault: cross cbo_zero, block_offset, priv_mode_m iff (ins.trap != 0);

endgroup

function void zic64b_sample(int hart, int issue, ins_t ins);
    Zic64b_cg.sample(ins);
endfunction
