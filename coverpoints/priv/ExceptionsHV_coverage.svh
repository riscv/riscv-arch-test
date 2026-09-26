///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Vector instructions with mstatus.VS and vsstatus.VS in each mode.
// Written: James Kaden Cassidy jacassidy@hmc.edu June 12 2025
// Modified: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSHV

covergroup ExceptionsHV_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // vtype.vill = 0, vstart = 0 and vl != 0 before the instruction, and no trap
    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                         get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                         get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                         ins.trap == 0} {
        bins true = {1'b1};
    }

    vector_instr: coverpoint ins.current.insn {
        wildcard bins csrr_vl = {CSRR} iff (ins.current.insn[31:20] == CSR_VL);
        wildcard bins vadd_vv = {VADD_VV};
        wildcard bins vsetvli = {VSETVLI};
    }
    vadd_vv: coverpoint ins.current.insn {
        wildcard bins vadd_vv = {VADD_VV};
    }
    vsetvli: coverpoint ins.current.insn {
        wildcard bins vsetvli = {VSETVLI};
    }
    mstatus_vs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins off   = {0};
        bins init  = {1};
        bins clean = {2};
        bins dirty = {3};
    }
    vsstatus_vs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vs") {
        bins off   = {0};
        bins init  = {1};
        bins clean = {2};
        bins dirty = {3};
    }
    mstatus_vs_clean: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins clean = {2};
    }
    vsstatus_vs_initial_clean: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "vs") {
        bins init  = {1};
        bins clean = {2};
    }

    // Illegal instruction when mstatus.VS = Off, or when V = 1 and vsstatus.VS = Off.  Otherwise vadd.vv and
    // vsetvli set mstatus.VS, and vsstatus.VS when V = 1, to Dirty
    cp_exceptionsHV_vs: cross priv_mode_hs_vs_u_vu, mstatus_vs, vsstatus_vs, vector_instr;

    // With V = 1, vector arithmetic and vsetvli set vsstatus.VS to Dirty from Initial or Clean
    cp_vsstatus_vs_set_dirty_arithmetic: cross priv_mode_vs_vu, std_vec, vadd_vv, mstatus_vs_clean, vsstatus_vs_initial_clean;
    cp_vsstatus_vs_set_dirty_csr:        cross priv_mode_vs_vu, std_vec, vsetvli, mstatus_vs_clean, vsstatus_vs_initial_clean;
endgroup

function void exceptionshv_sample(int hart, int issue, ins_t ins);
    ExceptionsHV_cg.sample(ins);
endfunction
