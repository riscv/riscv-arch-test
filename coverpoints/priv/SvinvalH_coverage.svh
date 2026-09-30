///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Svinval instructions in HS, VS, U and VU modes with mstatus.TVM = 0 and hstatus.VTVM = 0, 1, and
// invalidation of changed VS-stage and G-stage leaves.
// Written: Julia Gong jgong@g.hmc.edu November 10, 2025
//
// Copyright (C) 2025 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVINVALH

// Two-stage translation, for the invalidation tests
`ifdef UDB_MXLEN_64
    `ifdef UDB_SV39X4_TRANSLATION
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            `define SVINVALH_TWO_STAGE
        `endif
    `endif
`else
    `ifdef UDB_SV32X4_TRANSLATION
        `ifdef UDB_SV32_VSMODE_TRANSLATION
            `define SVINVALH_TWO_STAGE
        `endif
    `endif
`endif
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

    // The SFENCE.W.INVAL, HINVAL.VVMA or HINVAL.GVMA (or SINVAL.VMA in VS-mode), SFENCE.INVAL.IR sequence after a
    // VS-stage or G-stage leaf change, with x0 or a register in rs1 and rs2.  The test checks that the next guest
    // access uses the new leaf.
    `ifdef SVINVALH_TWO_STAGE
        hinval_vvma : coverpoint ins.current.insn {
            wildcard bins hinval_vvma = {HINVAL_VVMA};
        }
        hinval_gvma : coverpoint ins.current.insn {
            wildcard bins hinval_gvma = {HINVAL_GVMA};
        }
        sinval_vma : coverpoint ins.current.insn {
            wildcard bins sinval_vma = {SINVAL_VMA};
        }
        rs1 : coverpoint ins.current.insn[19:15] {
            bins x0       = {0};
            bins register = {[1:31]};
        }
        rs2 : coverpoint ins.current.insn[24:20] {
            bins x0       = {0};
            bins register = {[1:31]};
        }
        vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins paged = {[1:15]};
        }
        hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
            bins paged = {[1:15]};
        }

        cp_hinval_vvma   : cross priv_mode_hs, hinval_vvma, vsatp_paged, hgatp_paged, rs1, rs2;
        cp_hinval_gvma   : cross priv_mode_hs, hinval_gvma, vsatp_paged, hgatp_paged, rs1, rs2;
        cp_sinval_vma_vs : cross priv_mode_vs, sinval_vma, vsatp_paged, hgatp_paged, rs1, rs2;
    `endif
endgroup

function void svinvalh_sample(int hart, int issue, ins_t ins);
    SvinvalH_cg.sample(ins);
endfunction
