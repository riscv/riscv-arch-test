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
    lr_w_base_aligned: coverpoint ins.prev.rs1_val[5:0] {
        bins aligned_64 = {6'd0};
    }
    sc_offset: coverpoint ins.current.rs1_val[6:0] {
         bins offset_aligned[] = {[7'd0 : 7'd64]} with (item % 4 == 0);
    }

    cp_za64rs: cross  sc_w_instr, sc_offset, lr_w_instr, lr_w_base_aligned ;

endgroup

function void za64rs_sample(int hart, int issue, ins_t ins);
    Za64rs_cg.sample(ins);
endfunction
