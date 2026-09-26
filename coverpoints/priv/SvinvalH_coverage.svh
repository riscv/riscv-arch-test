///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Svinval instructions in HS, VS, U and VU modes with mstatus.TVM = 0 and hstatus.VTVM = 0, 1.
// Written: Julia Gong jgong@g.hmc.edu November 10, 2025
//
// Copyright (C) 2025 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVINVALH
covergroup SvinvalH_cg with function sample(ins_t ins);
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
    }
    hstatus_vtvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
        bins off = {0};
        bins on  = {1};
    }

    // mstatus.TVM = 1 and M-mode are in SvinvalHSm
    cp_svinval: cross priv_mode_hs_vs_u_vu, svinval, mstatus_tvm, hstatus_vtvm;
endgroup

function void svinvalh_sample(int hart, int issue, ins_t ins);
    SvinvalH_cg.sample(ins);
endfunction
