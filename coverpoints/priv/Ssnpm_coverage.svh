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

    pmm: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SENVCFG, "pmm") {
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

    mxr_bit: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "mxr")[0] {}

    `ifdef UDB_UXLEN_32  // UXL=01 is only reachable when U-mode supports RV32; checked from S-mode
        uxl_rv32: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "uxl") {
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

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
        // Fault cross confirms lw executed in U-mode at the illegal address.
        cp_hardware_csr_writes_fault_load: cross priv_mode_u, satp_mode, pmm, a_upper_bits, lw_insn, illegal_addr_load;
    `endif
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_STORE
        // Fault cross confirms sw executed in U-mode at the illegal address.
        cp_hardware_csr_writes_fault_store: cross priv_mode_u, satp_mode, pmm, a_upper_bits, sw_insn, illegal_addr_store;
    `endif

endgroup

`ifndef EXCLUDE_SM
covergroup Ssnpm_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SENVCFG, "pmm") {
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
        mseccfg_pmm: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSECCFG, "pmm") {
            bins pmm_00 = {2'b00};
            `ifdef UDB_SUPPORTED_PMLEN_SMMPM_7
                bins pmm_10 = {2'b10};
            `endif
            `ifdef UDB_SUPPORTED_PMLEN_SMMPM_16
                bins pmm_11 = {2'b11};
            `endif
        }
    `endif // SMMPM_SUPPORTED

    mxr_bit: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mxr")[0] {}
    mprv_bit: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mprv") {
        bins mprv_1 = {1'b1};   // MPRV=1: memory access uses MPP privilege
    }
    mpp_field_u: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "mpp") {
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

// H group: pointer masking in VS-mode and VU-mode and for HLV, HSV and HLVX (testplans/priv/Ssnpm_H.yaml).
//
`ifdef H_SUPPORTED
covergroup Ssnpm_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // Shared pointer-masking coverpoints: sw_lw_insn, jalr_insn, csrw_insn, misaligned_addr, pm_ssamoswap_insn,
    // pm_ssp_insn, lw_insn, sw_insn, illegal_addr_load and illegal_addr_store.
    `include "general/RISCV_coverage_pmm_coverpoints.svh"

    // ---- Instructions ----
    ld_sd: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins ld = {LD};
        wildcard bins sd = {SD};
    }
    hlv_hsv: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins hlv_d = {HLV_D};
        wildcard bins hsv_d = {HSV_D};
    }
    hlvx: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins hlvx_wu = {HLVX_WU};
    }
    // One variant of each memory-accessing instruction group, the .D form where there is one
    pm_h_insn: coverpoint ins.current.insn {
        type_option.weight = 0;
        `ifdef ZAAMO_SUPPORTED
            wildcard bins amoadd_d = {AMOADD_D};
            `ifdef ZACAS_SUPPORTED
                wildcard bins amocas_d = {AMOCAS_D};
            `endif
            `ifdef ZABHA_SUPPORTED
                wildcard bins amoadd_h = {AMOADD_H};
            `endif
        `endif
        `ifdef D_SUPPORTED
            wildcard bins fld = {FLD};
            wildcard bins fsd = {FSD};
        `endif
        `ifdef ZCA_SUPPORTED
            wildcard bins c_ld   = {C_LD};
            wildcard bins c_sd   = {C_SD};
            wildcard bins c_ldsp = {C_LDSP};
            wildcard bins c_sdsp = {C_SDSP};
            `ifdef ZCD_SUPPORTED
                wildcard bins c_fldsp = {C_FLDSP};
                wildcard bins c_fsdsp = {C_FSDSP};
            `endif
        `endif
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins cbo_zero = {CBO_ZERO};
        `endif
        `ifdef ZICBOM_SUPPORTED
            wildcard bins cbo_clean = {CBO_CLEAN};
        `endif
        // Hint with no architectural effect; the bin records only that it executed at the tagged address
        wildcard bins prefetch_w = {PREFETCH_W};
        `ifdef ZVE64X_SUPPORTED
            wildcard bins vle64_v     = {VLE64_V};
            wildcard bins vlse64_v    = {VLSE64_V};
            wildcard bins vluxei64_v  = {VLUXEI64_V};
            wildcard bins vloxei64_v  = {VLOXEI64_V};
            wildcard bins vlseg2e64_v = {VLSEG2E64_V};
            wildcard bins vl1re64_v   = {VL1RE64_V};
            wildcard bins vle64ff_v   = {VLE64FF_V};
            wildcard bins vse64_v     = {VSE64_V};
            wildcard bins vsse64_v    = {VSSE64_V};
            wildcard bins vsuxei64_v  = {VSUXEI64_V};
            wildcard bins vsoxei64_v  = {VSOXEI64_V};
            wildcard bins vsseg2e64_v = {VSSEG2E64_V};
            wildcard bins vs1r_v      = {VS1R_V};
        `endif
    }

    // ---- Tags: the address bits 63:48 of the effective address ----
    tag5: coverpoint (ins.current.eff_addr >> 48) {
        type_option.weight = 0;
        bins t0000 = {16'h0000};
        bins t0002 = {16'h0002}; // 0x0002 is bit 49 (PMLEN 16 only)
        bins t0400 = {16'h0400}; // 0x0400 is bit 58 (PMLEN 7 and 16)
        bins tFF00 = {16'hFF00}; // masked in full by PMLEN 16 and in part by PMLEN 7.
        bins tFFFF = {16'hFFFF}; // masked in full by PMLEN 16 and in part by PMLEN 7.
    }
    // A prefetch is an ori with rd = x0, which a run that does not collect Zicbop coverage decodes as ori, setting no
    // eff_addr.  Take its address from the encoding: rs1 (bits 19:15) plus bits 31:25 shifted left by 5.
    tag3: coverpoint (((ins.current.insn ==? PREFETCH_W) ?
                       (ins.prev.x_wdata[ins.current.insn[19:15]] + `UDB_MXLEN'(signed'({ins.current.insn[31:25], 5'b0}))) :
                       ins.current.eff_addr) >> 48) {
        type_option.weight = 0;
        bins t0000 = {16'h0000};
        bins t0400 = {16'h0400};
        bins tFFFF = {16'hFFFF};
    }
    ssp_tag: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSP, "ssp")[63:48] {
        type_option.weight = 0;
        bins t0000 = {16'h0000};
        bins t0400 = {16'h0400};
        bins tFFFF = {16'hFFFF};
    }

    // ---- Translation modes ----
    // All seven (vsatp.MODE, hgatp.MODE) pairs, each only when supported.  A paged pair needs both its VS-stage and
    // G-stage mode.
    pair_all: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSATP, "mode")[3:0],
                                  get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0]} {
        type_option.weight = 0;
        bins bare_bare = {8'h00};  // vsatp Bare, hgatp Bare
        `ifdef UDB_SV39X4_TRANSLATION
            bins bare_sv39x4 = {8'h08};  // vsatp Bare, hgatp Sv39x4
        `endif
        `ifdef UDB_SV48X4_TRANSLATION
            bins bare_sv48x4 = {8'h09};  // vsatp Bare, hgatp Sv48x4
        `endif
        `ifdef UDB_SV57X4_TRANSLATION
            bins bare_sv57x4 = {8'h0A};  // vsatp Bare, hgatp Sv57x4
        `endif
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            `ifdef UDB_SV39X4_TRANSLATION
                bins sv39_sv39x4 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
            `endif
        `endif
        `ifdef UDB_SV48_VSMODE_TRANSLATION
            `ifdef UDB_SV48X4_TRANSLATION
                bins sv48_sv48x4 = {8'h99};  // vsatp Sv48, hgatp Sv48x4
            `endif
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            `ifdef UDB_SV57X4_TRANSLATION
                bins sv57_sv57x4 = {8'hAA};  // vsatp Sv57, hgatp Sv57x4
            `endif
        `endif
    }
    // The widest bare pair, then the widest paged pair, the only pairs most coverpoints use.  The bare pair is the
    // first supported of (Bare, Sv57x4), (Bare, Sv48x4), (Bare, Sv39x4), (Bare, Bare).  The paged pair is the first
    // supported of (Sv57, Sv57x4), (Sv48, Sv48x4), (Sv39, Sv39x4), and absent without one.
    pair_chosen: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSATP, "mode")[3:0],
                                  get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0]} {
        type_option.weight = 0;
        `ifdef UDB_SV57X4_TRANSLATION
            bins bare_sv57x4 = {8'h0A};  // vsatp Bare, hgatp Sv57x4
        `elsif UDB_SV48X4_TRANSLATION
            bins bare_sv48x4 = {8'h09};  // vsatp Bare, hgatp Sv48x4
        `elsif UDB_SV39X4_TRANSLATION
            bins bare_sv39x4 = {8'h08};  // vsatp Bare, hgatp Sv39x4
        `else
            bins bare_bare = {8'h00};  // vsatp Bare, hgatp Bare
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            `ifdef UDB_SV57X4_TRANSLATION
                bins paged_sv57 = {8'hAA};  // vsatp Sv57, hgatp Sv57x4
            `else
                `ifdef UDB_SV48_VSMODE_TRANSLATION
                    `ifdef UDB_SV48X4_TRANSLATION
                        bins paged_sv48 = {8'h99};  // vsatp Sv48, hgatp Sv48x4
                    `else
                        `ifdef UDB_SV39_VSMODE_TRANSLATION
                            `ifdef UDB_SV39X4_TRANSLATION
                                bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
                            `endif
                        `endif
                    `endif
                `else
                    `ifdef UDB_SV39_VSMODE_TRANSLATION
                        `ifdef UDB_SV39X4_TRANSLATION
                            bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
                        `endif
                    `endif
                `endif
            `endif
        `else
            `ifdef UDB_SV48_VSMODE_TRANSLATION
                `ifdef UDB_SV48X4_TRANSLATION
                    bins paged_sv48 = {8'h99};  // vsatp Sv48, hgatp Sv48x4
                `else
                    `ifdef UDB_SV39_VSMODE_TRANSLATION
                        `ifdef UDB_SV39X4_TRANSLATION
                            bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
                        `endif
                    `endif
                `endif
            `else
                `ifdef UDB_SV39_VSMODE_TRANSLATION
                    `ifdef UDB_SV39X4_TRANSLATION
                        bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
                    `endif
                `endif
            `endif
        `endif
    }
    // The paged pair alone, for the shadow stack coverpoints
    pair_paged: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSATP, "mode")[3:0],
                                  get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0]} {
        type_option.weight = 0;
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            `ifdef UDB_SV57X4_TRANSLATION
                bins paged_sv57 = {8'hAA};  // vsatp Sv57, hgatp Sv57x4
            `else
                `ifdef UDB_SV48_VSMODE_TRANSLATION
                    `ifdef UDB_SV48X4_TRANSLATION
                        bins paged_sv48 = {8'h99};  // vsatp Sv48, hgatp Sv48x4
                    `else
                        `ifdef UDB_SV39_VSMODE_TRANSLATION
                            `ifdef UDB_SV39X4_TRANSLATION
                                bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
                            `endif
                        `endif
                    `endif
                `else
                    `ifdef UDB_SV39_VSMODE_TRANSLATION
                        `ifdef UDB_SV39X4_TRANSLATION
                            bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
                        `endif
                    `endif
                `endif
            `endif
        `else
            `ifdef UDB_SV48_VSMODE_TRANSLATION
                `ifdef UDB_SV48X4_TRANSLATION
                    bins paged_sv48 = {8'h99};  // vsatp Sv48, hgatp Sv48x4
                `else
                    `ifdef UDB_SV39_VSMODE_TRANSLATION
                        `ifdef UDB_SV39X4_TRANSLATION
                            bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
                        `endif
                    `endif
                `endif
            `else
                `ifdef UDB_SV39_VSMODE_TRANSLATION
                    `ifdef UDB_SV39X4_TRANSLATION
                        bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
                    `endif
                `endif
            `endif
        `endif
    }

    // ---- PMM fields ----
    // henvcfg.PMM applies to VS-mode, senvcfg.PMM to VU-mode and hstatus.HUPMM to HLV/HSV from U-mode
    henvcfg_pmm: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "pmm") {
        type_option.weight = 0;
        bins disabled = {2'b00};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    senvcfg_pmm: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SENVCFG, "pmm") {
        type_option.weight = 0;
        bins disabled = {2'b00};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    hstatus_hupmm: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "hupmm") {
        type_option.weight = 0;
        bins disabled = {2'b00};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    // henvcfg.PMM = senvcfg.PMM = hstatus.HUPMM, for the HLVX cases
    pmm_all_same: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "pmm")[1:0], get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SENVCFG, "pmm")[1:0], get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "hupmm")[1:0]} {
        type_option.weight = 0;
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {6'b10_10_10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {6'b11_11_11};
        `endif
    }
    // henvcfg.PMM and the tag, for the MXR, misaligned and stval/htval cases.  Tags that PMLEN masks in full: PMM 10
    // {0x0000, 0x0400}, PMM 11 {0x0000, 0xFFFF}.
    pmm_tag_h: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "pmm")[1:0], 16'(ins.current.eff_addr >> 48)} {
        type_option.weight = 0;
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7_t0000 = {{2'b10, 16'h0000}};
            bins pmlen7_t0400 = {{2'b10, 16'h0400}};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16_t0000 = {{2'b11, 16'h0000}};
            bins pmlen16_tFFFF = {{2'b11, 16'hFFFF}};
        `endif
    }
    // senvcfg.PMM and the tag, for the MXR, misaligned and stval/htval cases
    pmm_tag_s: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SENVCFG, "pmm")[1:0], 16'(ins.current.eff_addr >> 48)} {
        type_option.weight = 0;
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7_t0000 = {{2'b10, 16'h0000}};
            bins pmlen7_t0400 = {{2'b10, 16'h0400}};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16_t0000 = {{2'b11, 16'h0000}};
            bins pmlen16_tFFFF = {{2'b11, 16'hFFFF}};
        `endif
    }
    // vsstatus.MXR and sstatus.MXR: either one is MXR in effect for a guest access
    mxr_pair: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSSTATUS, "mxr")[0], get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSTATUS, "mxr")[0]} {
        type_option.weight = 0;
        bins vsstatus_0_sstatus_1 = {2'b01};
        bins vsstatus_1_sstatus_0 = {2'b10};
        bins vsstatus_1_sstatus_1 = {2'b11};
    }
    spvp_vs: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "spvp") {
        type_option.weight = 0;
        bins vs = {1};
    }
    spvp_vu: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "spvp") {
        type_option.weight = 0;
        bins vu = {0};
    }
    spvp: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "spvp") {
        type_option.weight = 0;
        bins spvp0 = {0};
        bins spvp1 = {1};
    }
    hstatus_hu: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "hu") {
        type_option.weight = 0;
        bins hu = {1};
    }

    // ---- Loads and stores in VS-mode and VU-mode ----
    cp_vs_pmm: cross priv_mode_vs, ld_sd, henvcfg_pmm, tag5, pair_all;
    cp_vu_pmm: cross priv_mode_vu, ld_sd, senvcfg_pmm, tag5, pair_all;

    // A write to senvcfg in VS-mode writes the real senvcfg.PMM.  The VU accesses that follow are cp_vu_pmm.
    csr_senvcfg: coverpoint ins.current.insn[31:20] {
        type_option.weight = 0;
        bins senvcfg = {CSR_SENVCFG};
    }
    senvcfg_pmm_written: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SENVCFG, "pmm") {
        type_option.weight = 0;
        bins disabled = {2'b00};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    cp_vu_pmm_writer_vs: cross priv_mode_vs, csrw_insn, csr_senvcfg, senvcfg_pmm_written;

    // ---- HLV and HSV from HS-mode: henvcfg.PMM with SPVP = 1, senvcfg.PMM with SPVP = 0 ----
    cp_hlv_hs_spvp1_pmm:     cross priv_mode_hs, hlv_hsv, spvp_vs, henvcfg_pmm, tag5, pair_chosen;
    cp_hlv_hs_spvp1_mxr_pmm: cross priv_mode_hs, hlv_hsv, spvp_vs, mxr_pair, pmm_tag_h, pair_chosen;
    cp_hlv_hs_spvp0_pmm:     cross priv_mode_hs, hlv_hsv, spvp_vu, senvcfg_pmm, tag5, pair_chosen;
    cp_hlv_hs_spvp0_mxr_pmm: cross priv_mode_hs, hlv_hsv, spvp_vu, mxr_pair, pmm_tag_s, pair_chosen;

    // ---- HLV and HSV from U-mode with hstatus.HU = 1: henvcfg.PMM with SPVP = 1, hstatus.HUPMM with SPVP = 0 ----
    cp_hlv_u_spvp1_pmm: cross priv_mode_u, hstatus_hu, hlv_hsv, spvp_vs, henvcfg_pmm, tag5, pair_chosen;
    cp_hlv_u_spvp0_pmm: cross priv_mode_u, hstatus_hu, hlv_hsv, spvp_vu, hstatus_hupmm, tag5, pair_chosen;

    // ---- HLVX is never masked, whichever PMM field applies ----
    cp_hlvx_hs_pmm: cross priv_mode_hs, hlvx, spvp, pmm_all_same, tag5, pair_chosen;
    cp_hlvx_u_pmm:  cross priv_mode_u, hstatus_hu, hlvx, spvp, pmm_all_same, tag5, pair_chosen;

    // ---- MXR turns masking off in VS-mode and VU-mode ----
    cp_vs_mxr_pmm: cross priv_mode_vs, ld_sd, mxr_pair, pmm_tag_h, pair_chosen;
    cp_vu_mxr_pmm: cross priv_mode_vu, ld_sd, mxr_pair, pmm_tag_s, pair_chosen;

    // ---- Every kind of memory-accessing instruction ----
    cp_vs_pmlen_masking: cross priv_mode_vs, pm_h_insn, henvcfg_pmm, tag3, pair_chosen;
    cp_vu_pmlen_masking: cross priv_mode_vu, pm_h_insn, senvcfg_pmm, tag3, pair_chosen;

    // ---- Zicfiss: SSAMOSWAP and ssp pushes and pops, paged pair only ----
    `ifdef ZICFISS_SUPPORTED
        cp_vs_pmlen_zicfiss_amo: cross priv_mode_vs, pm_ssamoswap_insn, henvcfg_pmm, tag3, pair_paged;
        cp_vu_pmlen_zicfiss_amo: cross priv_mode_vu, pm_ssamoswap_insn, senvcfg_pmm, tag3, pair_paged;
        cp_vs_pmlen_zicfiss_ssp: cross priv_mode_vs, pm_ssp_insn, henvcfg_pmm, ssp_tag, pair_paged;
        cp_vu_pmlen_zicfiss_ssp: cross priv_mode_vu, pm_ssp_insn, senvcfg_pmm, ssp_tag, pair_paged;
    `endif

    // ---- Instruction fetch is never masked ----
    cp_vs_pmm_jalr: cross priv_mode_vs, jalr_insn, henvcfg_pmm, tag5, pair_chosen;
    cp_vu_pmm_jalr: cross priv_mode_vu, jalr_insn, senvcfg_pmm, tag5, pair_chosen;

    // ---- Misaligned accesses, with fully masked tags ----
    cp_vs_pmlen_misaligned_word: cross priv_mode_vs, sw_lw_insn, misaligned_addr, pmm_tag_h, pair_chosen;
    cp_vu_pmlen_misaligned_word: cross priv_mode_vu, sw_lw_insn, misaligned_addr, pmm_tag_s, pair_chosen;

    // ---- stval and htval on a faulting access ----
    // The cause on the faulting instruction's record tells the two bases of the plan apart: an access fault (5 for a
    // load, 7 for a store) at RVMODEL_ACCESS_FAULT_ADDRESS_*, and a guest-page-fault (21, 23) at an address with no
    // G-stage mapping.  It also confirms that the access faulted.  H requires Sv39x4, so the guest-page-fault bins
    // do not depend on RVMODEL_ACCESS_FAULT_ADDRESS_*.
    lw_h: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lw = {LW};
    }
    sw_h: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins sw = {SW};
    }
    // The cause is sampled only on a trap.  Without the guard, a lw or sw that does not fault would fill a bin with
    // the cause of the previous trap.
    scause_load_fault: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code") iff (ins.current.trap) {
        type_option.weight = 0;
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
            bins load_access_fault = {LOAD_ACCESS_FAULT};
        `endif
        bins load_guest_page_fault = {LOAD_GUEST_PAGE_FAULT};
    }
    scause_store_fault: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code") iff (ins.current.trap) {
        type_option.weight = 0;
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_STORE
            bins store_access_fault = {STORE_AMO_ACCESS_FAULT};
        `endif
        bins store_guest_page_fault = {STORE_AMO_GUEST_PAGE_FAULT};
    }
    cp_vs_hardware_csr_writes_fault_load:  cross priv_mode_vs, lw_h, pmm_tag_h, pair_chosen, scause_load_fault;
    cp_vu_hardware_csr_writes_fault_load:  cross priv_mode_vu, lw_h, pmm_tag_s, pair_chosen, scause_load_fault;
    cp_vs_hardware_csr_writes_fault_store: cross priv_mode_vs, sw_h, pmm_tag_h, pair_chosen, scause_store_fault;
    cp_vu_hardware_csr_writes_fault_store: cross priv_mode_vu, sw_h, pmm_tag_s, pair_chosen, scause_store_fault;

    // ---- HFENCE.GVMA right after a PMM change ----
    // The test writes henvcfg or hstatus and execute hfence.gvma x0, x0 in the next instruction.
    hfence_gvma_rs1_x0: coverpoint ins.current.insn iff (ins.current.insn[19:15] == 5'b0) {
        type_option.weight = 0;
        wildcard bins hfence_gvma = {HFENCE_GVMA};
    }
    // The change coverpoints sample hgatp.MODE, then the PMM field before and after a write, on the instruction right
    // after the write.  ins.prev is the write, record 2 is the state before it and SAMPLE_BEFORE the state after it.
    //
    // They are split by G-stage mode, and each is compiled only where it has bins.  A coverpoint with no bins gets
    // automatic ones from SystemVerilog, and each HFENCE cross would then carry bins that cannot be hit.  The Sv57x4
    // ones (cases 1, 2 and 4 of the plan) need Sv57x4.  The Sv48x4 ones (case 3) need Sv48x4 and PMLEN 16.
    `ifdef UDB_SV57X4_TRANSLATION
        // hgatp.MODE, then henvcfg.PMM before and after a write to henvcfg, sampled on the instruction right after the
        // write.
        henvcfg_pmm_change: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0],
                                    get_csr_field(ins.hart, ins.issue, 2, CSR_HENVCFG, "pmm")[1:0],
                                    get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "pmm")[1:0]}
                        iff ((ins.prev.insn ==? CSRW) && (ins.prev.insn[31:20] == CSR_HENVCFG)) {
            type_option.weight = 0;
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
                bins sv57x4_00_to_10 = {{4'hA, 2'b00, 2'b10}};  // case 1
                bins sv57x4_10_to_00 = {{4'hA, 2'b10, 2'b00}};
            `endif
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
                bins sv57x4_00_to_11 = {{4'hA, 2'b00, 2'b11}};  // case 2
                bins sv57x4_11_to_00 = {{4'hA, 2'b11, 2'b00}};
                `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
                    bins sv57x4_10_to_11 = {{4'hA, 2'b10, 2'b11}};  // case 4
                    bins sv57x4_11_to_10 = {{4'hA, 2'b11, 2'b10}};
                `endif
            `endif
        }
        // hgatp.MODE, then hstatus.HUPMM before and after a write to hstatus, sampled on the instruction right after
        // the write.
        hupmm_change: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0],
                                    get_csr_field(ins.hart, ins.issue, 2, CSR_HSTATUS, "hupmm")[1:0],
                                    get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "hupmm")[1:0]}
                        iff ((ins.prev.insn ==? CSRW) && (ins.prev.insn[31:20] == CSR_HSTATUS)) {
            type_option.weight = 0;
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
                bins sv57x4_00_to_10 = {{4'hA, 2'b00, 2'b10}};  // case 1
                bins sv57x4_10_to_00 = {{4'hA, 2'b10, 2'b00}};
            `endif
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
                bins sv57x4_00_to_11 = {{4'hA, 2'b00, 2'b11}};  // case 2
                bins sv57x4_11_to_00 = {{4'hA, 2'b11, 2'b00}};
                `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
                    bins sv57x4_10_to_11 = {{4'hA, 2'b10, 2'b11}};  // case 4
                    bins sv57x4_11_to_10 = {{4'hA, 2'b11, 2'b10}};
                `endif
            `endif
        }
        cp_henvcfg_pmm_change_hfence: cross priv_mode_hs, hfence_gvma_rs1_x0, henvcfg_pmm_change;
        cp_hupmm_change_hfence:       cross priv_mode_hs, hfence_gvma_rs1_x0, hupmm_change;
    `endif // UDB_SV57X4_TRANSLATION
    `ifdef UDB_SV48X4_TRANSLATION
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            // Case 3: hgatp.MODE = Sv48x4, PMM 00 <-> 11.  Same expression and iff as henvcfg_pmm_change.
            henvcfg_pmm_change_sv48x4: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0],
                                        get_csr_field(ins.hart, ins.issue, 2, CSR_HENVCFG, "pmm")[1:0],
                                        get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "pmm")[1:0]}
                            iff ((ins.prev.insn ==? CSRW) && (ins.prev.insn[31:20] == CSR_HENVCFG)) {
                type_option.weight = 0;
                bins sv48x4_00_to_11 = {{4'h9, 2'b00, 2'b11}};  // case 3
                bins sv48x4_11_to_00 = {{4'h9, 2'b11, 2'b00}};
            }
            // Same expression and iff as hupmm_change
            hupmm_change_sv48x4: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0],
                                        get_csr_field(ins.hart, ins.issue, 2, CSR_HSTATUS, "hupmm")[1:0],
                                        get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "hupmm")[1:0]}
                            iff ((ins.prev.insn ==? CSRW) && (ins.prev.insn[31:20] == CSR_HSTATUS)) {
                type_option.weight = 0;
                bins sv48x4_00_to_11 = {{4'h9, 2'b00, 2'b11}};  // case 3
                bins sv48x4_11_to_00 = {{4'h9, 2'b11, 2'b00}};
            }
            cp_henvcfg_pmm_change_hfence_sv48x4: cross priv_mode_hs, hfence_gvma_rs1_x0, henvcfg_pmm_change_sv48x4;
            cp_hupmm_change_hfence_sv48x4:       cross priv_mode_hs, hfence_gvma_rs1_x0, hupmm_change_sv48x4;
        `endif // UDB_SUPPORTED_PMLEN_SSNPM_16
    `endif // UDB_SV48X4_TRANSLATION

    // ---- henvcfg.PMM change with no HFENCE right after it ----
    // The plan's cases: (vsatp, hgatp) = (Bare, Sv39x4), (Bare, Sv48x4) and (Sv57, Sv57x4).  The cross shows that
    // the change was not fenced right away; that no fence came later is checked by the signature.
    henvcfg_pmm_change_no_fence: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSATP, "mode")[3:0],
                                             get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0],
                                             get_csr_field(ins.hart, ins.issue, 2, CSR_HENVCFG, "pmm")[1:0],
                                             get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "pmm")[1:0]}
                    iff ((ins.prev.insn ==? CSRW) && (ins.prev.insn[31:20] == CSR_HENVCFG)) {
        type_option.weight = 0;
        `ifdef UDB_SV39X4_TRANSLATION
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
                bins bare_sv39x4_00_to_10 = {{4'h0, 4'h8, 2'b00, 2'b10}};  // case 1
                bins bare_sv39x4_10_to_00 = {{4'h0, 4'h8, 2'b10, 2'b00}};
            `endif
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
                bins bare_sv39x4_00_to_11 = {{4'h0, 4'h8, 2'b00, 2'b11}};  // case 2
                bins bare_sv39x4_11_to_00 = {{4'h0, 4'h8, 2'b11, 2'b00}};
            `endif
        `endif
        `ifdef UDB_SV48X4_TRANSLATION
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
                bins bare_sv48x4_00_to_10 = {{4'h0, 4'h9, 2'b00, 2'b10}};  // case 3
                bins bare_sv48x4_10_to_00 = {{4'h0, 4'h9, 2'b10, 2'b00}};
            `endif
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            `ifdef UDB_SV57X4_TRANSLATION
                `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
                    bins sv57_sv57x4_00_to_10 = {{4'hA, 4'hA, 2'b00, 2'b10}};  // case 4
                    bins sv57_sv57x4_10_to_00 = {{4'hA, 4'hA, 2'b10, 2'b00}};
                `endif
                `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
                    bins sv57_sv57x4_00_to_11 = {{4'hA, 4'hA, 2'b00, 2'b11}};  // case 5
                    bins sv57_sv57x4_11_to_00 = {{4'hA, 4'hA, 2'b11, 2'b00}};
                `endif
            `endif
        `endif
    }
    // Any instruction but hfence.gvma
    not_hfence_gvma: coverpoint ins.current.insn iff (!(ins.current.insn ==? HFENCE_GVMA)) {
        type_option.weight = 0;
        bins other = {[0:$]};
    }
    cp_henvcfg_pmm_change_no_hfence: cross priv_mode_hs, not_hfence_gvma, henvcfg_pmm_change_no_fence;

    // Case 3 access cross for hstatus.HUPMM: (vsatp, hgatp) = (Bare, Sv48x4), tag 0x0002 (bit 49), PMM 00 and 11.
    // It is cp_hlv_u_spvp0_pmm at (Bare, Sv48x4).  cp_hlv_u_spvp0_pmm samples only the widest bare pair, which is
    // Sv57x4 when it is supported.
    `ifdef UDB_SV48X4_TRANSLATION
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            hupmm_sv48x4_bit49: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSATP, "mode")[3:0],
                                            get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGATP, "mode")[3:0],
                                            get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS, "hupmm")[1:0],
                                            16'(ins.current.eff_addr >> 48)} {
                type_option.weight = 0;
                bins pmm00 = {{4'h0, 4'h9, 2'b00, 16'h0002}};  // vsatp Bare, hgatp Sv48x4
                bins pmm11 = {{4'h0, 4'h9, 2'b11, 16'h0002}};
            }
            cp_hlv_u_spvp0_sv48x4_pmm: cross priv_mode_u, hstatus_hu, spvp_vu, hlv_hsv, hupmm_sv48x4_bit49;
        `endif
    `endif

    // ---- PMM cleared when the XLEN of its mode becomes 32 ----
    // Once the XLEN field is 01 its PMM reads 00, so a later instruction cannot sample PMM 10 or 11 with the field at
    // 01.  The sample is the csrw that sets the field: the PMM before it and the field after it.  That the PMM reads
    // 00 afterwards is checked by the test.
    pmm_set_henvcfg: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HENVCFG, "pmm") {
        type_option.weight = 0;
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    pmm_set_senvcfg: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SENVCFG, "pmm") {
        type_option.weight = 0;
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    `ifdef UDB_VSXLEN_32
        csr_hstatus: coverpoint ins.current.insn[31:20] {
            type_option.weight = 0;
            bins hstatus = {CSR_HSTATUS};
        }
        vsxl_rv32_after: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HSTATUS, "vsxl") {
            type_option.weight = 0;
            bins vsxl_01 = {2'b01};
        }
        cp_pmm_vsxl_clear: cross priv_mode_hs, csrw_insn, csr_hstatus, pmm_set_henvcfg, vsxl_rv32_after;
    `endif
    `ifdef UDB_VUXLEN_32
        // vsstatus.UXL is written from HS-mode (csrw vsstatus) or from VS-mode (csrw sstatus)
        vsstatus_writer: coverpoint {ins.prev.mode_virt, ins.prev.mode, ins.current.insn[31:20]} {
            type_option.weight = 0;
            bins hs_vsstatus = {{3'b001, CSR_VSSTATUS}};
            bins vs_sstatus  = {{3'b101, CSR_SSTATUS}};
        }
        vsuxl_rv32_after: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSSTATUS, "uxl") {
            type_option.weight = 0;
            bins uxl_01 = {2'b01};
        }
        cp_pmm_vsuxl_clear: cross csrw_insn, vsstatus_writer, pmm_set_senvcfg, vsuxl_rv32_after;
    `endif

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
