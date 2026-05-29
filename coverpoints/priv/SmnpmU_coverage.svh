///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Smnpm (U-mode) — Machine-mode pointer masking for next lower privilege (U-mode, no S-mode).
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// Description:
//   Covers menvcfg.PMM configuration (PMM=00/10/11 → PMLEN=0/7/16) in M-mode
//   and its effect on U-mode memory accesses when S-mode is not present.
//   M-mode always operates in bare (PA) mode — no virtual addressing,
//   no sign-extension — so masked upper bits are always forced to zero.
//
//
//       PMM = 00 → PMLEN =  0  (masking disabled)
//       PMM = 10 → PMLEN =  7  (upper  7 bits ignored, bits [63:57])
//       PMM = 11 → PMLEN = 16  (upper 16 bits masked, bits [63:48])
//
///////////////////////////////////////////

`ifdef XLEN64
    `ifndef S_SUPPORTED
        `define COVER_SMNPMU

            covergroup SmnpmU_cg with function sample(ins_t ins);
            option.per_instance = 0;
            `include "general/RISCV_coverage_standard_coverpoints.svh"
            `include "general/RISCV_coverage_pmm_coverpoints.svh"

            pmm_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
                bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
                bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
                bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
            }
            uxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "uxl") {
                bins uxl_01 = {2'b01};
            }
            // menvcfg.PMM must have been cleared to 00 by hardware after UXL=01.
            pmm_after_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "pmm") {
                bins pmm_cleared = {2'b00};
            }
            // cp_pmlen_masking
            cp_pmlen_masking : cross priv_mode_u, pmm_bit, a_upper_bits, pm_insn ;
            // cp_pmlen_misaligned_word
            // One misaligned store and one misaligned load, PMLEN=7 only, upper 7 bits = 7'b1000000 or 7'b0000001
            cp_pm_misaligned_word: cross priv_mode_u, pm_misalign;
            // cp_pmm_uxl_clear
            iff (pmm_bit != 2'b00) {
                cp_pmm_uxl_clear: cross pmm_bit, uxl_rv32, pmm_after_clear;
            }
            // cp_hardware_csr_writes
            `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
                // Fault crosses confirm lw/sw executed in U-mode at the illegal address.
                cp_hardware_csr_writes_fault:   cross priv_mode_u, pm_fault;
            `endif

        endgroup

        function void smnpmu_sample(int hart, int issue, ins_t ins);
            SmnpmU_cg.sample(ins);
        endfunction
    `endif //S_SUPPORTED
`endif // XLEN64
