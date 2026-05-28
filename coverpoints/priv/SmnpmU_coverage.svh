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
//   A_masked is computed by the test generator.
//
//       PMM = 00 → PMLEN =  0  (masking disabled)
//       PMM = 10 → PMLEN =  7  (upper  7 bits ignored, bits [63:57])
//       PMM = 11 → PMLEN = 16  (upper 16 bits masked, bits [63:48])
//
//   Coverpoints:
//     cp_pmlen_masking_write  — write executed in U-mode at tagged address A;
//                               confirmed by read-back from A_masked.
//     cp_pmlen_masking_read   — read from A_masked returns the value written
//                               at A, proving the alias under active masking.
//     cp_pmlen_disabled       — PMM=00: A and A_masked resolve to different
//                               locations; read-back does not return sentinel.
//     cp_pmm_misaligned_word  — misaligned sw/lw at scratch+1, PMLEN=7,
//                               upper 7 bits = 0x00 and 0x01.
//     cp_hardware_csr_writes  — fault on illegal address in U-mode; mtval
//                               holds the correctly masked address after trap.
//     cp_pmm_uxl_clear        — hardware clears PMM when mstatus.UXL=01.
//
///////////////////////////////////////////


`define COVER_SMNPMU

`ifdef XLEN64
    `ifndef S_SUPPORTED
        covergroup SmnpmU_cg with function sample(ins_t ins);
        option.per_instance = 0;
        `include "general/RISCV_coverage_standard_coverpoints.svh"
        `include "general/RISCV_coverage_pmm_coverpoints.svh"

        pmm_active: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
            bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
        }
        pmm_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
            bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        }
        uxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "uxl") {
            bins uxl_01 = {2'b01};
        }
        // menvcfg.PMM must have been cleared to 00 by hardware after UXL=01.
        pmm_after_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "pmm") {
            bins pmm_cleared = {2'b00};
        }
        // When PMLEN=16, bare mode: upper 16 bits of mtval must be zeroed
        mtval_upper_pmm11_bare: coverpoint ins.current.csr[CSR_MTVAL][63:48]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b11) {
                bins mtval_zero = {16'h0000};   // bare mode — upper 16 bits always zeroed
        }
        // When PMLEN=7, bare mode: upper 7 bits of mtval must be zeroed
        mtval_upper_pmm10_bare: coverpoint ins.current.csr[CSR_MTVAL][63:57]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b10) {
                bins mtval_zero = {7'b0000000};  // bare mode — upper 7 bits always zeroed
        }

        // cp_pmlen_masking_write
        cp_pmlen_masking_write : cross priv_mode_u, pmm_active, a_upper_bits, pm_store_insn ;

        // cp_pmlen_masking_read
        // NOTE: A_masked (the read address) is computed by the test generator, not
        // sampled here.  The generator derives A_masked from A
        // by zeroing the upper PMLEN bits, so by construction
        // A_masked always has upper bits = 0x0000 (bare) depending on given PMM.
        // NOTE: RV64A / Zacas / Zabha have no standalone load instructions; their
        // read-backs use base lw/ld, already covered by the crosses above.
        // The Zicbom and Zicbop read-backs are already implied by the existing base load crosses — no duplication needed.

        cp_pmlen_masking_read : cross priv_mode_u, pmm_active, pm_load_insn ;

        // cp_pmlen_disabled[]
        cp_pmlen_disabled_lw: cross priv_mode_u, pmm_disabled, lw_insn;
        cp_pmlen_disabled_sw: cross priv_mode_u, a_upper_bits, pmm_disabled, sw_insn;

        // cp_pmlen_misaligned[]
        // One misaligned store and one misaligned load, PMLEN=7 only, upper 7 bits = 0 or 1
        cp_pm_misaligned_word_write: cross priv_mode_u, pm_misalign_write;
        cp_pm_misaligned_word_read:  cross priv_mode_u, pm_misalign_read;

        // cp_pmm_uxl_clear
        cp_pmm_uxl_clear: cross pmm_active, uxl_rv32, pmm_after_clear;

        // cp_hardware_csr_writes
        // Fault crosses confirm lw/sw executed in U-mode at the illegal address.
        // Trap crosses confirm mtval holds the correctly masked address after the fault.
        cp_hardware_csr_writes_read_fault:   cross priv_mode_u, pm_read_fault;
        cp_hardware_csr_writes_write_fault:  cross priv_mode_u, pm_write_fault;

        // PMM=11, Bare
        cp_hardware_csr_writes_read_pmm11_bare_trap:   cross priv_mode_m, mtval_upper_pmm11_bare, exception_occurred, lw_insn;
        cp_hardware_csr_writes_write_pmm11_bare_trap:  cross priv_mode_m, mtval_upper_pmm11_bare, exception_occurred, sw_insn;
        // PMM=10, Bare
        cp_hardware_csr_writes_read_pmm10_bare_trap:   cross priv_mode_m, mtval_upper_pmm10_bare, exception_occurred, lw_insn;
        cp_hardware_csr_writes_write_pmm10_bare_trap:  cross priv_mode_m, mtval_upper_pmm10_bare, exception_occurred, sw_insn;

        endgroup

        function void smnpmu_sample(int hart, int issue, ins_t ins);
            SmnpmU_cg.sample(ins);
        endfunction
    `endif //S_SUPPORTED
`endif // XLEN64
