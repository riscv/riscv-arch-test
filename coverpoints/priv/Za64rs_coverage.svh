///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written:  Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for Za64rs extension (Reservation sets are contiguous, naturally aligned, and a maximum of 64 bytes)
///////////////////////////////////////////////


`define COVER_ZA64RS

covergroup Za64rs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    lr_w_instr: coverpoint ins.prev.insn {
        wildcard bins lr_w = {LR_W};
    }
    sc_w_instr: coverpoint ins.current.insn {
        wildcard bins sc_w = {SC_W};
    }
    // Offset of the LR address inside its naturally aligned 64-byte block.
    lr_off_w: coverpoint ins.prev.rs1_val[5:0] {
        bins off[] = {[6'd0 : 6'd60]} with (item % 4 == 0);
    }
    // SC at the first word of the next block, or the last word of the previous block.
    sc_side_w: coverpoint ins.current.rs1_val[5:0] {
        bins next = {6'd0} iff (ins.current.rs1_val == (((ins.prev.rs1_val >> 6) << 6) + 64));
        bins prev = {6'd60} iff (ins.current.rs1_val == (((ins.prev.rs1_val >> 6) << 6) - 4));
    }
    cp_za64rs: cross sc_w_instr, lr_w_instr, lr_off_w, sc_side_w;

    `ifdef UDB_MXLEN_64
    lr_d_instr: coverpoint ins.prev.insn {
        wildcard bins lr_d = {LR_D};
    }
    sc_d_instr: coverpoint ins.current.insn {
        wildcard bins sc_d = {SC_D};
    }
    lr_off_d: coverpoint ins.prev.rs1_val[5:0] {
        bins off[] = {[6'd0 : 6'd56]} with (item % 8 == 0);
    }
    sc_side_d: coverpoint ins.current.rs1_val[5:0] {
        bins next = {6'd0} iff (ins.current.rs1_val == (((ins.prev.rs1_val >> 6) << 6) + 64));
        bins prev = {6'd56} iff (ins.current.rs1_val == (((ins.prev.rs1_val >> 6) << 6) - 8));
    }
    cp_za64rs_d: cross sc_d_instr, lr_d_instr, lr_off_d, sc_side_d;
    `endif

endgroup

function void za64rs_sample(int hart, int issue, ins_t ins);
    Za64rs_cg.sample(ins);
endfunction
