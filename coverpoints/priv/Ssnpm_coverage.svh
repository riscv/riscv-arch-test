///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Ssnpm — Supervisor-mode pointer masking for next lower privilege (U-mode).
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

`ifdef XLEN64
    `define COVER_SSNPM

        covergroup Ssnpm_cg with function sample(ins_t ins);
        option.per_instance = 0;
        `include "general/RISCV_coverage_standard_coverpoints.svh"
        `include "general/RISCV_coverage_pmm_coverpoints.svh"

        pmm_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "pmm") {
            bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
            bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
        }
        // ---- MXR bit from sstatus ----
        mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
            bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
            bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
        }
        uxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "uxl") {
            bins uxl_01 = {2'b01};
        }
        // senvcfg.PMM must have been cleared to 00 by hardware after UXL=01.
        pmm_after_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "pmm") {
            bins pmm_cleared = {2'b00};
        }
        // medeleg delegation witness — precondition, not a cross dimension
        medeleg_delegated: coverpoint ins.current.csr[CSR_MEDELEG][15:5] {
            // [10]=medeleg[15] [8]=medeleg[13] [2]=medeleg[7] [0]=medeleg[5]
            wildcard bins load_store_faults_delegated = {11'b1?1??????1?1};
        }
        //Main Crosses
        // cp_pmlen_masking_write
        cp_pmlen_masking : cross priv_mode_u, pmm_bit, satp_mode, a_upper_bits, pm_insn;
        // cp_pmlen_misaligned_word
        // One misaligned store and one misaligned load, PMLEN=7 only, upper 7 bits = 7'b1000000 or 7'b0000001
        cp_pmlen_misaligned_word: cross priv_mode_u, pm_misalign;
        // cp_pmm_mxr
        cp_pmm_mxr: cross priv_mode_u, pmm_bit,   mxr_bit, satp_mode, a_upper_bits, sw_lw_insn;
        // cp_pmm_jalr
        cp_pmm_jalr:      cross priv_mode_u, pmm_bit, a_upper_bits, mxr_bit, satp_mode, jalr_insn;
        // cp_pmm_uxl_clear
        iff (pmm_bit != 2'b00) {
            cp_pmm_uxl_clear: cross pmm_bit, uxl_rv32, pmm_after_clear;
        }
        // cp_hardware_csr_writes
        // Fault crosses confirm lw/sw executed in U-mode at the illegal address.
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
            cp_hardware_csr_writes_fault:   cross priv_mode_u, satp_mode, pm_fault;
        `endif

    endgroup

    function void ssnpm_sample(int hart, int issue, ins_t ins);
        Ssnpm_cg.sample(ins);
    endfunction

`endif  // XLEN64
