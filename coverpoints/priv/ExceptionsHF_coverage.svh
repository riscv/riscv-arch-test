///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Floating-point instructions with mstatus.FS and vsstatus.FS in each mode.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSHF

covergroup ExceptionsHF_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    fp_instr: coverpoint ins.current.insn {
        wildcard bins csrr_fcsr = {CSRR} iff (ins.current.insn[31:20] == CSR_FCSR);
        wildcard bins fadd_s    = {FADD_S};
    }
    mstatus_fs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins off   = {0};
        bins init  = {1};
        bins clean = {2};
        bins dirty = {3};
    }
    vsstatus_fs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "fs") {
        bins off   = {0};
        bins init  = {1};
        bins clean = {2};
        bins dirty = {3};
    }

    // Illegal instruction when mstatus.FS = Off, or when V = 1 and vsstatus.FS = Off.  Otherwise fadd.s sets
    // mstatus.FS, and vsstatus.FS when V = 1, to Dirty
    cp_exceptionsHF_fs: cross priv_mode_hs_vs_u_vu, mstatus_fs, vsstatus_fs, fp_instr;
endgroup

function void exceptionshf_sample(int hart, int issue, ins_t ins);
    ExceptionsHF_cg.sample(ins);
endfunction
