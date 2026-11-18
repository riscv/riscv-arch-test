///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SSCOUNTERENW
covergroup Sscounterenw_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    scounteren_csr: coverpoint ins.current.insn[31:20] {
        wildcard bins scounteren = {CSR_SCOUNTEREN};
    }
    scounteren_ones_zeros: coverpoint ins.current.rs1_val[31:0] {
            bins all_zeros  =   {32'b00000000000000000000000000000000};
            bins all_ones   =   {32'b11111111111111111111111111111111};
    }
    cp_scounteren_writable: cross priv_mode_s, csrrw, scounteren_csr, scounteren_ones_zeros;

    // The self-check masks the S-mode scounteren read with one bit built by slli.
    // Bits [24:20] of that slli are the counter index, so each n in 3..31 is its own bin.
    // Reading mhpmcounter is not sampled: that read happens even when the counter is
    // read-only zero and the bit check is skipped.
    `ifdef ZIHPM_SUPPORTED
    hpm_bit_and: coverpoint ins.current.insn {
        wildcard bins and_inst = {AND} iff (ins.trap == 0);
    }
    hpm_bit_slli: coverpoint ins.prev.insn {
        wildcard bins slli = {SLLI} iff (ins.trap == 0);
    }
    hpm_bit_shamt: coverpoint ins.prev.insn[24:20] {
        bins n[] = {[5'd3:5'd31]} iff (ins.trap == 0);
    }
    cp_hpmcounter_scounteren: cross priv_mode_s, hpm_bit_and, hpm_bit_slli, hpm_bit_shamt;
    `endif

endgroup

function void sscounterenw_sample(int hart, int issue, ins_t ins);
    Sscounterenw_cg.sample(ins);
endfunction
