///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Smnpm (S-mode) — Machine-mode pointer masking for next lower privilege (S-mode if it exists).
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// Description:
//   Covers menvcfg.PMM configuration (PMM=00/10/11 → PMLEN=0/7/16) in M-mode
//   and its effect on S-mode memory accesses across all supported  modes
//   (Bare, Sv39, Sv48, Sv57).  When PMM is active, hardware strips the upper
//   PMLEN bits of the effective address before the access reaches PMP/MMU,
//   so a tagged address A and its masked form  alias to the same
//   physical location.
//
///////////////////////////////////////////

`ifdef XLEN64
    `ifdef S_SUPPORTED
        `define COVER_SMNPMS

            covergroup SmnpmS_cg with function sample(ins_t ins);
            option.per_instance = 0;
            `include "general/RISCV_coverage_standard_coverpoints.svh"
            `include "general/RISCV_coverage_pmm_coverpoints.svh"

            pmm_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
                bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
                bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
                bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
            }
            // ---- MXR bit from sstatus ----
            mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
                bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
                bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
            }
            sxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sxl") {
                bins sxl_01 = {2'b01};
            }
            // menvcfg.PMM must have been cleared to 00 by hardware after SXL=01.
            pmm_after_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "pmm") {
                bins pmm_cleared = {2'b00};
            }
            // medeleg delegation witness — precondition, not a cross dimension
            medeleg_delegated: coverpoint ins.current.csr[CSR_MEDELEG][15:5] {
                // [10]=medeleg[15] [8]=medeleg[13] [2]=medeleg[7] [0]=medeleg[5]
                wildcard bins load_store_faults_delegated = {11'b1?1??????1?1};
            }
            // ---- CSR write/read instructions ----
            csr_rw_insn: coverpoint ins.current.insn {
                wildcard bins csrrw = {CSRRW};
                wildcard bins csrr = {CSRR};
            }
            // ---- Target CSR address (sepc, stvec, sscratch) ----
            csr_target: coverpoint ins.current.insn[31:20] { //excluding read-only csrs
                bins sepc     = {CSR_SEPC};
                //bins stvec    = {CSR_STVEC}; //// warl field has complex write restrictions and is not easy to test
                bins sscratch = {CSR_SSCRATCH};
            }

            // cp_pmlen_masking
            cp_pmlen_masking : cross priv_mode_s, pmm_bit, satp_mode, a_upper_bits, pm_insn ;
            // cp_pmlen_misaligned_word
            // One misaligned store and one misaligned load, PMLEN=7 only, upper 7 bits = 7'b1000000 or 7'b0000001
            cp_pm_misaligned_word: cross priv_mode_s, pm_misalign;
            // cp_pmm_mxr
            cp_pmm_mxr: cross priv_mode_s, pmm_bit, mxr_bit, satp_mode, a_upper_bits, sw_lw_insn;
            // cp_pmm_addr_mode_jalr — not guarded by S_SUPPORTED; implicit fetch is
            // never pointer-masked regardless of PMM or MXR availability.
            cp_pmm_jalr: cross priv_mode_s, pmm_bit, a_upper_bits, mxr_bit, satp_mode, jalr_insn;
            // cp_pmm_sxl_clear
            iff (pmm_bit != 2'b00) {
                cp_pmm_sxl_clear: cross pmm_bit, sxl_rv32, pmm_after_clear;
            }
            // cp_hardware_csr_writes
            `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
                // Fault crosses confirm lw/sw executed in S-mode at the illegal address.
                cp_hardware_csr_writes_fault:   cross priv_mode_s, satp_mode, pm_fault;
            `endif
            // cp_pm_csr_software_access
            cp_pm_csr_software_access: cross priv_mode_s, pmm_bit, csr_target, csr_rw_insn;

        endgroup

        function void smnpms_sample(int hart, int issue, ins_t ins);
            SmnpmS_cg.sample(ins);
        endfunction
    `endif //S_SUPPORTED
`endif // XLEN64
