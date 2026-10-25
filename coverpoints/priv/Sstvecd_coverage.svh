///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
// stvec is also covered by S_scsr_cg (cp_stvec_vaddr_walk1/walk0/pc/scratch), which every
// Sstvecd configuration samples; see coverpoints/norm/Sstvecd.yaml.
`define COVER_SSTVECD
covergroup Sstvecd_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    stvec: coverpoint ins.current.insn[31:20] {
        bins stvec = {CSR_STVEC};
    }
    xaddr_pc: coverpoint (ins.current.rs1_val + 4 == ins.current.pc_rdata) {
        bins pc = {1};
    }
    xaddr_scratch: coverpoint (ins.current.rs1_val[7:0] == 8'hA8) {
        bins scratch = {1};
    }
    cp_stvec_vaddr_pc:      cross priv_mode_s, csrrw, stvec, xaddr_pc;
    cp_stvec_vaddr_scratch: cross priv_mode_s, csrrw, stvec, xaddr_scratch;

    // Canonical addresses have bits XLEN-1:VALEN-1 equal, so bit VALEN-2 is the msb walked on its own.
    // BASE holds the address with MODE = Direct, so bits 1:0 stay 0.
    `ifdef SV57_SUPPORTED
        `define SSTVECD_VADDR_WALK_MSB 55
    `elsif SV48_SUPPORTED
        `define SSTVECD_VADDR_WALK_MSB 46
    `elsif SV39_SUPPORTED
        `define SSTVECD_VADDR_WALK_MSB 37
    `elsif SV32_SUPPORTED
        `define SSTVECD_VADDR_WALK_MSB 31
    `endif
    `ifdef SSTVECD_VADDR_WALK_MSB
        stvec_vaddr_walk1: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
            bins b_1[] = { [2:`SSTVECD_VADDR_WALK_MSB] };
        }
        stvec_vaddr_walk0: coverpoint $clog2(~(ins.current.rs1_val | 3))
                           iff ($onehot(~(ins.current.rs1_val | 3))) {
            bins b_0[] = { [2:`SSTVECD_VADDR_WALK_MSB] };
        }
        cp_stvec_vaddr_walk1: cross priv_mode_s, csrrw, stvec, stvec_vaddr_walk1;
        cp_stvec_vaddr_walk0: cross priv_mode_s, csrrw, stvec, stvec_vaddr_walk0;
    `endif
endgroup

function void sstvecd_sample(int hart, int issue, ins_t ins);
    Sstvecd_cg.sample(ins);
endfunction
