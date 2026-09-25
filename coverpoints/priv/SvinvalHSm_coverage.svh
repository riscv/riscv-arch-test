///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Svinval instructions in M-mode with mstatus.TVM = 0, 1, and in HS, VS, U and VU modes with
// mstatus.TVM = 1, each with hstatus.VTVM = 0, 1.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVINVALHSM
covergroup SvinvalHSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    svinval: coverpoint ins.current.insn {
        wildcard bins sfence_w_inval  = {SFENCE_W_INVAL};
        wildcard bins sinval_vma      = {SINVAL_VMA};
        wildcard bins sfence_inval_ir = {SFENCE_INVAL_IR};
        wildcard bins hinval_vvma     = {HINVAL_VVMA};
        wildcard bins hinval_gvma     = {HINVAL_GVMA};
    }
    mstatus_tvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins off = {0};
        bins on  = {1};
    }
    mstatus_tvm_on: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins on = {1};
    }
    hstatus_vtvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
        bins off = {0};
        bins on  = {1};
    }

    // SvinvalH covers the lower modes with mstatus.TVM = 0
    cp_svinval_m:   cross priv_mode_m, svinval, mstatus_tvm, hstatus_vtvm;
    cp_svinval_tvm: cross priv_mode_hs_vs_u_vu, svinval, mstatus_tvm_on, hstatus_vtvm;
endgroup

function void svinvalhsm_sample(int hart, int issue, ins_t ins);
    SvinvalHSm_cg.sample(ins);
endfunction
