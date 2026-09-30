///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: David Harris David_Harris@hmc.edu 29 September 2026
//
// Copyright (C) 2026 RISC-V International
// SPDX-License-Identifier: Apache-2.0
//
// Description: Ssnpm pointer masking in VS-mode, VU-mode and for HLV/HSV/HLVX
//
// The accesses run with vsatp = Bare, so masking zero-extends guest physical addresses.
// Each address has one tag bit set; the test checks whether the access reached its data.
///////////////////////////////////////////////

`define COVER_SSNPMH

covergroup SsnpmH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    ld_sd: coverpoint ins.current.insn {
        wildcard bins ld = {LD};
        wildcard bins sd = {SD};
    }
    ld: coverpoint ins.current.insn {
        wildcard bins ld = {LD};
    }
    hlv_hsv: coverpoint ins.current.insn {
        wildcard bins hlv_d = {HLV_D};
        wildcard bins hsv_d = {HSV_D};
    }
    hlvx: coverpoint ins.current.insn {
        wildcard bins hlvx_wu = {HLVX_WU};
    }

    // Tag bits of the address (rs1; the offset is 0): masked by PMLEN = 7 and 16, or by PMLEN = 16 only
    tag: coverpoint {(ins.current.rs1_val[63:57] != 0), (ins.current.rs1_val[56:48] != 0)} {
        bins pmlen7  = {2'b10};
        bins pmlen16 = {2'b01};
    }

    vsatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    // Guest physical address widths whose top bits (49 or 58) pointer masking can clear
    hgatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins sv48x4 = {9};
        bins sv57x4 = {10};
    }
    spvp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        bins vu = {0};
        bins vs = {1};
    }

    // The PMM field that applies to the access: henvcfg.PMM in VS-mode and for HLV/HSV/HLVX with SPVP = 1,
    // senvcfg.PMM in VU-mode and for them from HS-mode with SPVP = 0, hstatus.HUPMM from U-mode with SPVP = 0
    applicable_pmm: coverpoint
        (ins.prev.mode_virt ? (ins.prev.mode == 2'b01 ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm")
                                                      : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm")) :
         get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") ?
             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm") :
         ins.prev.mode == 2'b01 ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm")
                                : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hupmm")) {
        bins disabled = {0};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {3};
        `endif
    }
    applicable_pmm_enabled: coverpoint
        (ins.prev.mode_virt ? (ins.prev.mode == 2'b01 ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm")
                                                      : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm")) :
         get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") ?
             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm") :
         ins.prev.mode == 2'b01 ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm")
                                : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hupmm")) {
        bins enabled = {[2:3]};
    }
    vsstatus_mxr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins mxr = {1};
    }

    // Loads and stores in VS-mode (henvcfg.PMM) and VU-mode (senvcfg.PMM)
    cp_vs_pmm: cross priv_mode_vs, ld_sd, applicable_pmm, tag, vsatp_bare, hgatp_mode;
    cp_vu_pmm: cross priv_mode_vu, ld_sd, applicable_pmm, tag, vsatp_bare, hgatp_mode;

    // HLV and HSV from HS-mode and from U-mode with hstatus.HU = 1
    cp_hlv_hs_pmm: cross priv_mode_hs, hlv_hsv, spvp, applicable_pmm, tag, vsatp_bare, hgatp_mode;
    cp_hlv_u_pmm:  cross priv_mode_u,  hlv_hsv, spvp, applicable_pmm, tag, vsatp_bare, hgatp_mode;

    // HLVX is never masked
    cp_hlvx_pmm: cross priv_mode_s_u, hlvx, spvp, applicable_pmm_enabled, tag, vsatp_bare, hgatp_mode;

    // vsstatus.MXR = 1 turns masking off in VS-mode and VU-mode
    cp_mxr_pmm: cross priv_mode_vs_vu, ld, vsstatus_mxr, applicable_pmm_enabled, tag, vsatp_bare, hgatp_mode;

endgroup

function void ssnpmh_sample(int hart, int issue, ins_t ins);
    SsnpmH_cg.sample(ins);
endfunction
