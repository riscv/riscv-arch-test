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

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr")[0] {}

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

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr")[0] {}
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

// H group: pointer masking in VS-mode and VU-mode and for HLV, HSV and HLVX (testplans/priv/Ssnpm_H.yaml).
//
// (vsatp.MODE, hgatp.MODE) pairs.  A paged pair needs both its VS-stage and G-stage mode.
`ifdef UDB_SV39_VSMODE_TRANSLATION
    `ifdef UDB_SV39X4_TRANSLATION
        `define SSNPMH_SV39_PAIR
    `endif
`endif
`ifdef UDB_SV48_VSMODE_TRANSLATION
    `ifdef UDB_SV48X4_TRANSLATION
        `define SSNPMH_SV48_PAIR
    `endif
`endif
`ifdef UDB_SV57_VSMODE_TRANSLATION
    `ifdef UDB_SV57X4_TRANSLATION
        `define SSNPMH_SV57_PAIR
    `endif
`endif
`ifdef SSNPMH_SV39_PAIR
    `define SSNPMH_ANY_PAGED_PAIR
`elsif SSNPMH_SV48_PAIR
    `define SSNPMH_ANY_PAGED_PAIR
`elsif SSNPMH_SV57_PAIR
    `define SSNPMH_ANY_PAGED_PAIR
`endif

// PMM and tag bins for the misaligned and stval/htval cases.  Tags a PMLEN masks in full: PMM 10 {0x0000, 0x0400},
// PMM 11 {0xFFFF}.  Tags 0x0000 and 0x0400 are already covered by PMM 10.
`ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
    `define SSNPMH_PMM_TAG_BINS_7 \
        bins pmlen7_t0000 = {2'b10, 16'h0000}; \
        bins pmlen7_t0400 = {2'b10, 16'h0400};
`else
    `define SSNPMH_PMM_TAG_BINS_7
`endif
`ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
    `define SSNPMH_PMM_TAG_BINS_16 \
        bins pmlen16_tFFFF = {2'b11, 16'hFFFF};
`else
    `define SSNPMH_PMM_TAG_BINS_16
`endif

// {vsatp.MODE, hgatp.MODE} as sampled before the instruction
`define SSNPMH_PAIR_VALUE \
    {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[3:0], \
     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")[3:0]}

// BARE_PAIR bin: the widest supported of (Bare, Sv57x4), (Bare, Sv48x4), (Bare, Sv39x4), (Bare, Bare)
`ifdef UDB_SV57X4_TRANSLATION
    `define SSNPMH_BARE_PAIR_BIN \
        bins bare_sv57x4 = {8'h0A};  // vsatp Bare, hgatp Sv57x4
`elsif UDB_SV48X4_TRANSLATION
    `define SSNPMH_BARE_PAIR_BIN \
        bins bare_sv48x4 = {8'h09};  // vsatp Bare, hgatp Sv48x4
`elsif UDB_SV39X4_TRANSLATION
    `define SSNPMH_BARE_PAIR_BIN \
        bins bare_sv39x4 = {8'h08};  // vsatp Bare, hgatp Sv39x4
`else
    `define SSNPMH_BARE_PAIR_BIN \
        bins bare_bare = {8'h00};  // vsatp Bare, hgatp Bare
`endif
// PAGED_PAIR bin: the widest supported of (Sv57, Sv57x4), (Sv48, Sv48x4), (Sv39, Sv39x4).  Empty without a paged pair.
`ifdef SSNPMH_SV57_PAIR
    `define SSNPMH_PAGED_PAIR_BIN \
        bins paged_sv57 = {8'hAA};  // vsatp Sv57, hgatp Sv57x4
`elsif SSNPMH_SV48_PAIR
    `define SSNPMH_PAGED_PAIR_BIN \
        bins paged_sv48 = {8'h99};  // vsatp Sv48, hgatp Sv48x4
`elsif SSNPMH_SV39_PAIR
    `define SSNPMH_PAGED_PAIR_BIN \
        bins paged_sv39 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
`else
    `define SSNPMH_PAGED_PAIR_BIN
`endif

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
    // hfence.gvma with rs1 = x0; rs2 is x0 or a VMID
    hfence_gvma_rs1_x0: coverpoint ins.current.insn iff (ins.current.insn[19:15] == 5'b0) {
        type_option.weight = 0;
        wildcard bins hfence_gvma = {HFENCE_GVMA};
    }

    // ---- Tags: the address bits 63:48 of rs1 ----
    tag5: coverpoint ((ins.current.rs1_val + ins.current.imm) >> 48) {
        type_option.weight = 0;
        bins t0000 = {16'h0000};
        bins t0002 = {16'h0002}; // 0x0002 is bit 49 (PMLEN 16 only)
        bins t0400 = {16'h0400}; // 0x0400 is bit 58 (PMLEN 7 and 16)
        bins tFF00 = {16'hFF00}; // masked in full by PMLEN 16 and in part by PMLEN 7.
        bins tFFFF = {16'hFFFF}; // masked in full by PMLEN 16 and in part by PMLEN 7.
    }
    tag3: coverpoint ((ins.current.rs1_val + ins.current.imm) >> 48) {
        type_option.weight = 0;
        bins t0000 = {16'h0000};
        bins t0400 = {16'h0400};
        bins tFFFF = {16'hFFFF};
    }
    ssp_tag: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp")[63:48] {
        type_option.weight = 0;
        bins t0000 = {16'h0000};
        bins t0400 = {16'h0400};
        bins tFFFF = {16'hFFFF};
    }

    // ---- Translation modes ----
    // All seven (vsatp.MODE, hgatp.MODE) pairs, each only when supported
    pair_all: coverpoint `SSNPMH_PAIR_VALUE {
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
        `ifdef SSNPMH_SV39_PAIR
            bins sv39_sv39x4 = {8'h88};  // vsatp Sv39, hgatp Sv39x4
        `endif
        `ifdef SSNPMH_SV48_PAIR
            bins sv48_sv48x4 = {8'h99};  // vsatp Sv48, hgatp Sv48x4
        `endif
        `ifdef SSNPMH_SV57_PAIR
            bins sv57_sv57x4 = {8'hAA};  // vsatp Sv57, hgatp Sv57x4
        `endif
    }
    // The widest bare pair and the widest paged pair, the only pairs most coverpoints use
    pair_chosen: coverpoint `SSNPMH_PAIR_VALUE {
        type_option.weight = 0;
        `SSNPMH_BARE_PAIR_BIN
        `SSNPMH_PAGED_PAIR_BIN
    }
    // The paged pair alone, for the shadow stack coverpoints
    `ifdef SSNPMH_ANY_PAGED_PAIR
        pair_paged: coverpoint `SSNPMH_PAIR_VALUE {
            type_option.weight = 0;
            `SSNPMH_PAGED_PAIR_BIN
        }
    `endif

    // ---- PMM fields ----
    // henvcfg.PMM applies to VS-mode, senvcfg.PMM to VU-mode and hstatus.HUPMM to HLV/HSV from U-mode
    henvcfg_pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm") {
        type_option.weight = 0;
        bins disabled = {2'b00};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    senvcfg_pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm") {
        type_option.weight = 0;
        bins disabled = {2'b00};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    hstatus_hupmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hupmm") {
        type_option.weight = 0;
        bins disabled = {2'b00};
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {2'b10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {2'b11};
        `endif
    }
    // The largest supported PMM value
    // henvcfg.PMM = senvcfg.PMM = hstatus.HUPMM, for the HLVX cases
    pmm_all_same: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm")[1:0], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm")[1:0], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hupmm")[1:0]} {
        type_option.weight = 0;
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
            bins pmlen7 = {6'b10_10_10};
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            bins pmlen16 = {6'b11_11_11};
        `endif
    }
    // henvcfg.PMM and the tag, for the misaligned and stval/htval cases
    pmm_tag_h: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm")[1:0], 16'((ins.current.rs1_val + ins.current.imm) >> 48)} {
        type_option.weight = 0;
        `SSNPMH_PMM_TAG_BINS_7
        `SSNPMH_PMM_TAG_BINS_16
    }
    // senvcfg.PMM and the tag, for the misaligned and stval/htval cases
    pmm_tag_s: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm")[1:0], 16'((ins.current.rs1_val + ins.current.imm) >> 48)} {
        type_option.weight = 0;
        `SSNPMH_PMM_TAG_BINS_7
        `SSNPMH_PMM_TAG_BINS_16
    }
    // vsstatus.MXR and sstatus.MXR: either one is MXR in effect for a guest access
    mxr_pair: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr")[0]} {
        type_option.weight = 0;
        bins vsstatus_0_sstatus_1 = {2'b01};
        bins vsstatus_1_sstatus_0 = {2'b10};
        bins vsstatus_1_sstatus_1 = {2'b11};
    }
    spvp_vs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        type_option.weight = 0;
        bins vs = {1};
    }
    spvp_vu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        type_option.weight = 0;
        bins vu = {0};
    }
    spvp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        type_option.weight = 0;
        bins spvp0 = {0};
        bins spvp1 = {1};
    }
    hstatus_hu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu") {
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
    senvcfg_pmm_written: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "pmm") {
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

    // The VS stage produces a GPA whose top bit is in the masked range; masking must not clear it.  The accesses use
    // an untagged VA, so the sampled state is the PMM value and the paged pair.  Sv48x4 (bit 49) needs PMLEN 16.
    gstage_case: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[3:0], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")[3:0], get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pmm")[1:0]} {
        type_option.weight = 0;
        `ifdef SSNPMH_SV48_PAIR
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
                bins sv48_pmlen16 = {10'b1001_1001_11};
            `endif
        `endif
        `ifdef SSNPMH_SV57_PAIR
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_7
                bins sv57_pmlen7 = {10'b1010_1010_10};
            `endif
            `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
                bins sv57_pmlen16 = {10'b1010_1010_11};
            `endif
        `endif
    }
    cp_vs_gstage_no_pmm: cross priv_mode_vs, ld_sd, gstage_case;

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
        `ifdef SSNPMH_ANY_PAGED_PAIR
            cp_vs_pmlen_zicfiss_amo: cross priv_mode_vs, pm_ssamoswap_insn, henvcfg_pmm, tag3, pair_paged;
            cp_vu_pmlen_zicfiss_amo: cross priv_mode_vu, pm_ssamoswap_insn, senvcfg_pmm, tag3, pair_paged;
            cp_vs_pmlen_zicfiss_ssp: cross priv_mode_vs, pm_ssp_insn, henvcfg_pmm, ssp_tag, pair_paged;
            cp_vu_pmlen_zicfiss_ssp: cross priv_mode_vu, pm_ssp_insn, senvcfg_pmm, ssp_tag, pair_paged;
        `endif
    `endif

    // ---- Instruction fetch is never masked ----
    cp_vs_pmm_jalr: cross priv_mode_vs, jalr_insn, henvcfg_pmm, tag5, pair_chosen;
    cp_vu_pmm_jalr: cross priv_mode_vu, jalr_insn, senvcfg_pmm, tag5, pair_chosen;

    // ---- Misaligned accesses, with fully masked tags ----
    cp_vs_pmlen_misaligned_word: cross priv_mode_vs, sw_lw_insn, misaligned_addr, pmm_tag_h, pair_chosen;
    cp_vu_pmlen_misaligned_word: cross priv_mode_vu, sw_lw_insn, misaligned_addr, pmm_tag_s, pair_chosen;

    // ---- stval and htval on a faulting access.  The guest-page-fault base has no fixed address, so only the
    // access-fault base is distinguished. ----
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
        cp_vs_hardware_csr_writes_fault_load: cross priv_mode_vs, lw_insn, pmm_tag_h, pair_chosen, illegal_addr_load;
        cp_vu_hardware_csr_writes_fault_load: cross priv_mode_vu, lw_insn, pmm_tag_s, pair_chosen, illegal_addr_load;
    `endif
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_STORE
        cp_vs_hardware_csr_writes_fault_store: cross priv_mode_vs, sw_insn, pmm_tag_h, pair_chosen, illegal_addr_store;
        cp_vu_hardware_csr_writes_fault_store: cross priv_mode_vu, sw_insn, pmm_tag_s, pair_chosen, illegal_addr_store;
    `endif

    // ---- HFENCE.GVMA after a PMM change ----
    // The tagged accesses of these tests are cp_vs_pmm and cp_hlv_u_spvp0_pmm.  Whether a stale translation is used
    // after the change is checked by the signature.  Only the fence is sampled here.
    cp_henvcfg_pmm_change_hfence: cross priv_mode_hs, hfence_gvma_rs1_x0, henvcfg_pmm;
    cp_hupmm_change_hfence:      cross priv_mode_hs, hfence_gvma_rs1_x0, hstatus_hupmm;
    // Case 3 of cp_hupmm_change_hfence: (vsatp, hgatp) = (Bare, Sv48x4), tag 0x0002 (bit 49), PMM 00 and 11.
    // cp_hlv_u_spvp0_pmm samples only the widest bare pair, which is Sv57x4 when it is supported.
    `ifdef UDB_SV48X4_TRANSLATION
        `ifdef UDB_SUPPORTED_PMLEN_SSNPM_16
            hupmm_sv48x4_bit49: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[3:0],
                                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")[3:0],
                                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hupmm")[1:0],
                                            16'((ins.current.rs1_val + ins.current.imm) >> 48)} {
                type_option.weight = 0;
                bins pmm00 = {4'h0, 4'h9, 2'b00, 16'h0002};  // vsatp Bare, hgatp Sv48x4
                bins pmm11 = {4'h0, 4'h9, 2'b11, 16'h0002};
            }
            cp_hupmm_change_hfence_sv48x4: cross priv_mode_u, hstatus_hu, spvp_vu, hlv_hsv, hupmm_sv48x4_bit49;
        `endif
    `endif

    // ---- PMM cleared when the XLEN of its mode becomes 32 ----
    // The inputs are the mode, the PMM value that was set, and the XLEN field being 01.  That PMM reads 00 afterwards
    // is checked by the test.
    `ifdef UDB_VSXLEN_32
        vsxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vsxl") {
            type_option.weight = 0;
            bins vsxl_01 = {2'b01};
        }
        cp_pmm_vsxl_clear: cross priv_mode_hs, henvcfg_pmm, vsxl_rv32;
    `endif
    `ifdef UDB_VUXLEN_32
        vsuxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "uxl") {
            type_option.weight = 0;
            bins uxl_01 = {2'b01};
        }
        // vsstatus.UXL is written from HS-mode (csrw vsstatus) or from VS-mode (csrw sstatus)
        cp_pmm_vsuxl_clear: cross priv_mode_hs_vs, senvcfg_pmm, vsuxl_rv32;
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
