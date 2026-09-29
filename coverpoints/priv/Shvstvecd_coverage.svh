///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Shvstvecd: vstvec holds MODE = Direct with every valid 4-byte-aligned address.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SHVSTVECD
covergroup Shvstvecd_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    vstvec: coverpoint ins.current.insn[31:20] {
        bins vstvec = {CSR_VSTVEC};
    }
    xaddr_pc: coverpoint (ins.current.rs1_val + 4 == ins.current.pc_rdata) {
        bins pc = {1};
    }
    xaddr_scratch: coverpoint (ins.current.rs1_val[7:0] == 8'hA8) {
        bins scratch = {1};
    }
    cp_vstvec_vaddr_pc:      cross priv_mode_hs, csrrw, vstvec, xaddr_pc;
    cp_vstvec_vaddr_scratch: cross priv_mode_hs, csrrw, vstvec, xaddr_scratch;

    // Canonical addresses have bits XLEN-1:VALEN-1 equal, so bit VALEN-2 is the msb walked on its own.
    // BASE holds the address with MODE = Direct, so bits 1:0 stay 0.
    `ifdef SV57_SUPPORTED
        `define SHVSTVECD_VADDR_WALK_MSB 55
    `elsif SV48_SUPPORTED
        `define SHVSTVECD_VADDR_WALK_MSB 46
    `elsif SV39_SUPPORTED
        `define SHVSTVECD_VADDR_WALK_MSB 37
    `elsif SV32_SUPPORTED
        `define SHVSTVECD_VADDR_WALK_MSB 31
    `endif
    `ifdef SHVSTVECD_VADDR_WALK_MSB
        vstvec_vaddr_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [2:`SHVSTVECD_VADDR_WALK_MSB] };
        }
        vstvec_vaddr_walk0: coverpoint $clog2(~(ins.current.rs1_val | 3))
                            iff ($onehot(~(ins.current.rs1_val | 3))) {
            bins b_0[] = { [2:`SHVSTVECD_VADDR_WALK_MSB] };
        }
        cp_vstvec_vaddr_walk1: cross priv_mode_hs, csrrw, vstvec, vstvec_vaddr_walk1;
        cp_vstvec_vaddr_walk0: cross priv_mode_hs, csrrw, vstvec, vstvec_vaddr_walk0;
    `endif
endgroup

function void shvstvecd_sample(int hart, int issue, ins_t ins);
    Shvstvecd_cg.sample(ins);
endfunction
