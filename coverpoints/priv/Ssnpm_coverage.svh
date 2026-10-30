///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Ssnpm — Supervisor-mode pointer masking for next lower privilege (U-mode).
// Group Sm: M-mode pointer masking under MPRV with MPP=U (senvcfg.PMM governs).
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
//
// Description:
//   Covers senvcfg.PMM configuration (PMM=00/10/11 → PMLEN=0/7/16) in S-mode
//   and its effect on U-mode memory accesses across all supported VM modes
//   (Bare, Sv39, Sv48, Sv57).  When PMM is active, hardware strips the upper
//   PMLEN bits of the effective address before the access reaches PMP/MMU,
//   so a tagged address A and its masked form alias to the same
//   physical location.
//
///////////////////////////////////////////

`define COVER_SSNPM

covergroup Ssnpm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
        `endif
    }

    //Declare pmm before including the shared PMM coverpoint file so the include can reference it.
    `include "general/RISCV_coverage_pmm_coverpoints.svh"

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
        bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
        bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
    }

    `ifdef UDB_UXLEN_32  // UXL=01 is only reachable when U-mode supports RV32; checked from S-mode
        uxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "uxl") {
            bins uxl_01 = {2'b01};
        }
    `endif // UDB_UXLEN_32

    //Main Crosses
    cp_pmlen_masking : cross priv_mode_u, pmm, satp_mode, a_upper_bits, pm_insn;
    `ifdef ZICFISS_SUPPORTED
        cp_pmlen_zicfiss_amo : cross priv_mode_u, pmm, satp_mode_zicfiss, a_upper_bits, pm_ssamoswap_insn;
        cp_pmlen_zicfiss_ssp : cross priv_mode_u, pmm, satp_mode_zicfiss, ssp_upper_bits, pm_ssp_insn;
    `endif // ZICFISS_SUPPORTED
    cp_pmlen_misaligned_word: cross priv_mode_u, satp_mode, pmm, a_upper_bits, sw_lw_insn, misaligned_addr;
    cp_pmm_mxr: cross priv_mode_u, pmm, a_upper_bits, mxr_bit, satp_mode, sw_lw_insn;
    cp_pmm_jalr: cross priv_mode_u, pmm, a_upper_bits, mxr_bit, satp_mode, jalr_insn;
    `ifdef UDB_UXLEN_32
        cp_pmm_uxl_clear: cross priv_mode_s, pmm, uxl_rv32;
    `endif // UDB_UXLEN_32

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Fault crosses confirm lw/sw executed in U-mode at the illegal address.
        cp_hardware_csr_writes_fault: cross priv_mode_u, satp_mode, pmm, a_upper_bits, sw_lw_insn, illegal_addr;
    `endif

endgroup

`ifndef EXCLUDE_SM
covergroup Ssnpm_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
        `endif
    }

    //Declare pmm before including the shared PMM coverpoint file so the include can reference it.
    `include "general/RISCV_coverage_pmm_coverpoints.svh"

    `ifdef SMMPM_SUPPORTED  // mseccfg.PMM exists only with Smmpm; it must not apply here
        mseccfg_pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mseccfg", "pmm") {
            bins pmm_00 = {2'b00};
            `ifdef UDB_SUPPORTED_PMLEN_SMMPM_7
                bins pmm_10 = {2'b10};
            `endif
            `ifdef UDB_SUPPORTED_PMLEN_SMMPM_16
                bins pmm_11 = {2'b11};
            `endif
        }
    `endif // SMMPM_SUPPORTED

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
        bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
    }
    mprv_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins mprv_1 = {1'b1};   // MPRV=1: memory access uses MPP privilege
    }
    mpp_field_u: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        bins mpp_u = {2'b00};   // effective privilege = U-mode
    }

    // Main Cross
    `ifdef SMMPM_SUPPORTED
        cp_pm_mprv_mpp_u: cross priv_mode_m, pmm, mseccfg_pmm, mprv_bit, mxr_bit, satp_mode_mprv, a_upper_bits_mprv, sw_lw_insn, mpp_field_u;
    `else
        cp_pm_mprv_mpp_u: cross priv_mode_m, pmm, mprv_bit, mxr_bit, satp_mode_mprv, a_upper_bits_mprv, sw_lw_insn, mpp_field_u;
    `endif // SMMPM_SUPPORTED

endgroup
`endif // EXCLUDE_SM

// H group: pointer masking in VS-mode and VU-mode and for HLV, HSV and HLVX.  The accesses run with vsatp = Bare,
// so masking zero-extends guest physical addresses.  Each address has one tag bit set; the test checks whether
// the access reached its data.
`ifdef H_SUPPORTED
covergroup Ssnpm_H_cg with function sample(ins_t ins);
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
    spvp_vu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        bins vu = {0};
    }
    spvp_vs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        bins vs = {1};
    }
    hstatus_hu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu") {
        bins hu = {1};
    }

    // PMM fields: henvcfg.PMM applies to VS-mode, senvcfg.PMM to VU-mode and hstatus.HUPMM to HLV/HSV from U-mode
    henvcfg_pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm") {
        bins disabled = {0};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {3};
        `endif
    }
    senvcfg_pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm") {
        bins disabled = {0};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {3};
        `endif
    }
    hstatus_hupmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hupmm") {
        bins disabled = {0};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {3};
        `endif
    }
    henvcfg_pmm_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm") {
        bins enabled = {[2:3]};
    }
    senvcfg_pmm_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm") {
        bins enabled = {[2:3]};
    }
    hstatus_hupmm_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hupmm") {
        bins enabled = {[2:3]};
    }
    vsstatus_mxr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins mxr = {1};
    }

    // Loads and stores in VS-mode (henvcfg.PMM) and VU-mode (senvcfg.PMM)
    cp_vs_pmm: cross priv_mode_vs, ld_sd, henvcfg_pmm, tag, vsatp_bare, hgatp_mode;
    cp_vu_pmm: cross priv_mode_vu, ld_sd, senvcfg_pmm, tag, vsatp_bare, hgatp_mode;

    // HLV and HSV from HS-mode: henvcfg.PMM with SPVP = 1, senvcfg.PMM with SPVP = 0
    cp_hlv_hs_spvp1_pmm: cross priv_mode_hs, hlv_hsv, spvp_vs, henvcfg_pmm, tag, vsatp_bare, hgatp_mode;
    cp_hlv_hs_spvp0_pmm: cross priv_mode_hs, hlv_hsv, spvp_vu, senvcfg_pmm, tag, vsatp_bare, hgatp_mode;

    // HLV and HSV from U-mode with hstatus.HU = 1: henvcfg.PMM with SPVP = 1, hstatus.HUPMM with SPVP = 0
    cp_hlv_u_spvp1_pmm: cross priv_mode_u, hstatus_hu, hlv_hsv, spvp_vs, henvcfg_pmm, tag, vsatp_bare, hgatp_mode;
    cp_hlv_u_spvp0_pmm: cross priv_mode_u, hstatus_hu, hlv_hsv, spvp_vu, hstatus_hupmm, tag, vsatp_bare, hgatp_mode;

    // HLVX is never masked, whichever PMM field applies
    cp_hlvx_hs_pmm: cross priv_mode_hs, hlvx, spvp, henvcfg_pmm_enabled, senvcfg_pmm_enabled, tag, vsatp_bare, hgatp_mode;
    cp_hlvx_u_pmm: cross priv_mode_u, hstatus_hu, hlvx, spvp, henvcfg_pmm_enabled, hstatus_hupmm_enabled, tag, vsatp_bare, hgatp_mode;

    // vsstatus.MXR = 1 turns masking off in VS-mode and VU-mode
    cp_mxr_pmm: cross priv_mode_vs_vu, ld, vsstatus_mxr, henvcfg_pmm_enabled, senvcfg_pmm_enabled, tag, vsatp_bare, hgatp_mode;

endgroup
`endif // H_SUPPORTED

function void ssnpm_sample(int hart, int issue, ins_t ins);
    Ssnpm_cg.sample(ins);
    `ifndef EXCLUDE_SM
        Ssnpm_Sm_cg.sample(ins);
    `endif
    `ifdef H_SUPPORTED
        Ssnpm_H_cg.sample(ins);
    `endif
endfunction
