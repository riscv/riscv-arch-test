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
//   so a tagged address A and its masked form A_masked alias to the same
//   physical location.  A_masked is computed by the test generator.
//
//   Coverpoints:
//     cp_pmlen_masking_write  — write executed in S-mode at tagged address A;
//                               confirmed by read-back from A_masked.
//     cp_pmlen_masking_read   — read from A_masked returns the value written
//                               at A, proving the alias under active masking.
//     cp_pmlen_disabled       — PMM=00: A and A_masked resolve to different
//                               locations; read-back does not return the value at A.
//     cp_pmm_mxr_addr_mode    — MXR interaction: masking suppressed when MXR=1;
//                               implicit fetch (jalr) never masked regardless.
//     cp_pmm_misaligned_word  — misaligned sw/lw at scratch+1, PMLEN=7,
//                               upper 7 bits = 0x00 and 0x01.
//     cp_hardware_csr_writes  — fault on illegal address in S-mode; stval in
//                               S-mode trap handler holds the masked address.
//     cp_pmm_sxl_clear        — hardware clears PMM when mstatus.SXL=01.
//     cp_pm_csr_software      — CSR reads/writes with upper PMLEN bits set;
//                               masking must NOT be applied to CSR accesses.
//
///////////////////////////////////////////

`define COVER_SMNPMS

`ifdef XLEN64
    `ifdef S_SUPPORTED


        covergroup SmnpmS_cg with function sample(ins_t ins);
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
        // When PMLEN =16  and  {{PMLEN{effective_address[XLEN-PMLEN-1]}} = 0
        stval_upper_pmm11_va_sign_zero: coverpoint ins.current.csr[CSR_STVAL][63:48]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b11 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode")  != 4'b0000  &&
            (ins.current.rs1_val + ins.current.imm)[47] == 1'b0)  {
                bins stval_zero = {16'h0000};   //  sign-bit=0 VA
        }
        // when PMLEN =16  and {{PMLEN{effective_address[XLEN-PMLEN-1]}} = 1
        stval_upper_pmm11_va_sign_one: coverpoint ins.current.csr[CSR_STVAL][63:48]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b11 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode")  != 4'b0000  &&
            (ins.current.rs1_val + ins.current.imm)[47] == 1'b1)  {
                bins stval_ones = {16'hFFFF};   // sign-bit=1 VA (Sv39/48/57)
        }
        stval_upper_pmm11_bare: coverpoint ins.current.csr[CSR_STVAL][63:48]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b11 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode")  == 4'b0000) {
                bins stval_zero = {16'h0000};   // bare mode
        }
        // PMM=10, Bare: sign_ext_ones impossible — upper 7 always zeroed
        stval_upper_pmm10_bare: coverpoint ins.current.csr[CSR_STVAL][63:57]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b10 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode")  == 4'b0000) {
                bins sign_ext_zero = {7'b0000000};
        }
        // when PMLEN =7  and {{PMLEN{effective_address[XLEN-PMLEN-1]}} = 1
        stval_upper_pmm10_va_sign_one: coverpoint ins.current.csr[CSR_STVAL][63:57]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b10 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") != 4'b0000&&
            (ins.current.rs1_val + ins.current.imm)[56] == 1'b1) {
                bins sign_ext_ones = {7'b1111111};
        }
        // when PMLEN =7  and {{PMLEN{effective_address[XLEN-PMLEN-1]}} = 0
        stval_upper_pmm10_va_sign_zero: coverpoint ins.current.csr[CSR_STVAL][63:57]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b10 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") != 4'b0000&&
            (ins.current.rs1_val + ins.current.imm)[56] == 1'b0) {
                bins sign_ext_zero = {7'b0000000};
        }

        // medeleg delegation witness — precondition, not a cross dimension
        medeleg_delegated: coverpoint ins.current.csr[CSR_MEDELEG][15:5] {
            // [10]=medeleg[15] [8]=medeleg[13] [2]=medeleg[7] [0]=medeleg[5]
            wildcard bins load_store_faults_delegated = {11'b1?1??????1?1};
        }
        // ---- CSR write/read instructions ----
        csr_write_insn: coverpoint ins.current.insn {
            wildcard bins csrrw = {CSRRW};
        }
        csr_read_insn: coverpoint ins.current.insn {
            wildcard bins csrr = {CSRR};
        }
        // ---- Target CSR address (sepc, stvec, sscratch) ----
        csr_target: coverpoint ins.current.insn[31:20] { //excluding read-only csrs
            bins sepc     = {CSR_SEPC};
            //bins stvec    = {CSR_STVEC}; //// warl field has complex write restrictions and is not easy to test
            bins sscratch = {CSR_SSCRATCH};
        }

        // cp_pmlen_masking_write
        cp_pmlen_masking_write : cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, pm_store_insn ;

        // cp_pmlen_masking_read
        // NOTE: A_masked (the read address) is computed by the test generator, not
        // sampled here. The generator derives A_masked from A by zeroing /
        // sign-extending the upper PMLEN bits per menvcfg.PMM and satp.MODE.
        // NOTE: RV64A / Zacas / Zabha have no standalone load instructions; their
        // read-backs use base lw/ld, already covered by the crosses above.
        // The Zicbom and Zicbop read-backs are already implied by the existing base load crosses — no duplication needed.
        cp_pmlen_masking_read: cross priv_mode_s, pmm_active, satp_mode, pm_load_insn;

        // cp_pmlen_disabled[]
        cp_pmlen_disabled_lw: cross priv_mode_s, pmm_disabled, satp_mode, lw_insn;
        cp_pmlen_disabled_sw: cross priv_mode_s, a_upper_bits, pmm_disabled, satp_mode, sw_insn;

        // cp_pmlen_misaligned[]
        // One misaligned store and one misaligned load, PMLEN=7 only, upper 7 bits = 0 or 1
        cp_pm_misaligned_word_write: cross priv_mode_s, pm_misalign_write;
        cp_pm_misaligned_word_read:  cross priv_mode_s, pm_misalign_read;

        // cp_pmm_mxr_addr_mode_write
        cp_pmm_mxr_addr_mode_write_pmm_active_mxr: cross priv_mode_s, pmm_active, mxr_bit, satp_mode, a_upper_bits, sw_insn;
        // cp_pmm_mxr_addr_mode_read
        cp_pmm_mxr_addr_mode_read_pmm_active_mxr:  cross priv_mode_s, pmm_active, mxr_bit, satp_mode, lw_insn;

        // never pointer-masked regardless of PMM or MXR availability.
        cp_pmm_addr_mode_jalr: cross priv_mode_s, pmm_active, a_upper_bits, mxr_bit, satp_mode, jalr_insn, jalr_a_upper_bits_nonzero;

        // cp_pmm_sxl_clear
        cp_pmm_sxl_clear: cross pmm_active, sxl_rv32, pmm_after_clear;

        // =======================================================================
        // cp_hardware_csr_writes
        // =======================================================================
        // Fault crosses confirm lw/sw executed in S-mode at the illegal address.
        // Trap crosses confirm stval holds the correctly masked address in the
        // S-mode handler (medeleg must be set to delegate faults to S-mode).
        cp_hardware_csr_writes_read_fault:   cross priv_mode_u, pm_read_fault;
        cp_hardware_csr_writes_write_fault:  cross priv_mode_u, pm_write_fault;

        // PMM=11, Bare
        cp_hardware_csr_writes_read_pmm11_bare_trap:          cross priv_mode_s, stval_upper_pmm11_bare, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm11_bare_trap:         cross priv_mode_s, stval_upper_pmm11_bare, exception_occurred, medeleg_delegated, sw_insn;
        // PMM=11, VA, sign bit=0
        cp_hardware_csr_writes_read_pmm11_va_sign_zero_trap:   cross priv_mode_s, stval_upper_pmm11_va_sign_zero, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm11_va_sign_zero_trap:  cross priv_mode_s, stval_upper_pmm11_va_sign_zero, exception_occurred, medeleg_delegated, sw_insn;
        // PMM=11, VA, sign bit=1
        cp_hardware_csr_writes_read_pmm11_va_sign_one_trap:    cross priv_mode_s, stval_upper_pmm11_va_sign_one, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm11_va_sign_one_trap:   cross priv_mode_s, stval_upper_pmm11_va_sign_one, exception_occurred, medeleg_delegated, sw_insn;
        // PMM=10, Bare
        cp_hardware_csr_writes_read_pmm10_bare_trap:           cross priv_mode_s, stval_upper_pmm10_bare, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm10_bare_trap:          cross priv_mode_s, stval_upper_pmm10_bare, exception_occurred, medeleg_delegated, sw_insn;
        // PMM=10, VA, sign bit=0
        cp_hardware_csr_writes_read_pmm10_va_sign_zero_trap:   cross priv_mode_s, stval_upper_pmm10_va_sign_zero, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm10_va_sign_zero_trap:  cross priv_mode_s, stval_upper_pmm10_va_sign_zero, exception_occurred, medeleg_delegated, sw_insn;
        // PMM=10, VA, sign bit=1
        cp_hardware_csr_writes_read_pmm10_va_sign_one_trap:    cross priv_mode_s, stval_upper_pmm10_va_sign_one, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm10_va_sign_one_trap:   cross priv_mode_s, stval_upper_pmm10_va_sign_one, exception_occurred, medeleg_delegated, sw_insn;

        // =======================================================================
        // cp_pm_csr_software_access_write / cp_pm_csr_software_access_read
        // =======================================================================
        // Pointer masking must NOT be applied to software CSR reads/writes.
        cp_pm_csr_software_access_write: cross priv_mode_s, pmm_active, csr_target, csr_write_insn;
        cp_pm_csr_software_access_read:  cross priv_mode_s, pmm_active, csr_target, csr_read_insn;

        endgroup

        function void smnpms_sample(int hart, int issue, ins_t ins);
            SmnpmS_cg.sample(ins);
        endfunction
    `endif //S_SUPPORTED
`endif // XLEN64
