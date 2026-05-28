///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Smmpm — Machine-mode pointer masking (M-mode self-masking).
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// Description:
//   Covers mseccfg.PMM configuration (PMM=00/10/11 → PMLEN=0/7/16) and its
//   effect on M-mode memory accesses.  M-mode always operates in bare (PA)
//   mode — no virtual addressing, no sign-extension — so masked upper bits
//   are always forced to zero.  A_masked is computed by the test generator.
//
//       PMM = 00 → PMLEN =  0  (masking disabled)
//       PMM = 10 → PMLEN =  7  (upper  7 bits ignored, bits [63:57])
//       PMM = 11 → PMLEN = 16  (upper 16 bits masked, bits [63:48])
//
//   Coverpoints:
//     cp_pmlen_masking_write  — write in M-mode at tagged address A;
//                               confirmed by read-back from A_masked.
//     cp_pmlen_masking_read   — read from A_masked returns value written
//                               at A, proving the alias under active masking.
//     cp_pmlen_disabled       — PMM=00: A and A_masked resolve to different
//                               locations; read-back does not return sentinel.
//     cp_pmm_mxr_addr_mode    — MXR interaction (S_SUPPORTED only): masking
//                               suppressed when MXR=1; implicit fetch (jalr)
//                               never masked regardless of PMM or MXR.
//     cp_pmm_misaligned_word  — misaligned sw/lw at scratch+1, PMLEN=7,
//                               upper 7 bits = 0x00 and 0x01.
//     cp_hardware_csr_writes  — fault on illegal address in M-mode; mtval
//                               holds the correctly masked address after trap.
//     cp_pm_mprv              — MPRV=1 with MPP=U/S: masking uses the PMM
//                               settings of the effective privilege mode.
//     cp_pm_csr_software      — CSR reads/writes with upper PMLEN bits set;
//                               masking must NOT be applied to CSR accesses.
//
///////////////////////////////////////////

`define COVER_SMMPM

`ifdef XLEN64

    covergroup Smmpm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_pmm_coverpoints.svh"

    pmm_active: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mseccfg", "pmm") {
        bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
    }
    pmm_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mseccfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
    }
    `ifdef S_SUPPORTED  //As MXR is read-only zero if S mode is not supported
    // ---- MXR bit from sstatus ----
        mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
            bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
            bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
        }
    `endif
    // When PMLEN=16, bare mode: upper 16 bits of mtval must be zeroed
    mtval_upper_pmm11_bare: coverpoint ins.current.csr[CSR_MTVAL][63:48]
        iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mseccfg", "pmm") == 2'b11) {
            bins mtval_zero = {16'h0000};   // bare mode — upper 16 bits always zeroed
    }
    // When PMLEN=7, bare mode: upper 7 bits of mtval must be zeroed
    mtval_upper_pmm10_bare: coverpoint ins.current.csr[CSR_MTVAL][63:57]
        iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mseccfg", "pmm") == 2'b10) {
            bins mtval_zero = {7'b0000000};  // bare mode — upper 7 bits always zeroed
    }
    // ---- MPRV bit from mstatus ----
    mprv_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins mprv_1 = {1'b1};   // MPRV=1: memory access uses MPP privilege
    }
    // ---- MPP field from mstatus ----
    mpp_field: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        `ifdef U_SUPPORTED
            bins mpp_u = {2'b00};   // effective privilege = U-mode
        `endif
        `ifdef S_SUPPORTED
            bins mpp_s = {2'b01};   // effective privilege = S-mode
        `endif
    }
    // ---- CSR write/read instructions ----
    csr_write_insn: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    csr_read_insn: coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    // ---- Target CSR address (mepc, mtvec, mscratch) ----
    csr_target: coverpoint ins.current.insn[31:20] { //excluding read-only csrs
        bins mepc     = {CSR_MEPC};
        //bins mtvec    = {CSR_MTVEC}; //// warl field has complex write restrictions and is not easy to test
        bins mscratch = {CSR_MSCRATCH};
    }

    // cp_pmlen_masking_write
    cp_pmlen_masking_write : cross priv_mode_m, pmm_active, a_upper_bits, pm_store_insn ;

    // =======================================================================
    // cp_pmlen_masking_read
    // =======================================================================
    // NOTE: A_masked (the read address) is computed by the test generator, not
    // sampled here. The generator derives A_masked from A by zeroing the upper
    // PMLEN bits; M-mode always runs bare so upper bits are always zeroed.
    // NOTE: RV64A / Zacas / Zabha have no standalone load instructions; their
    // read-backs use base lw/ld, already covered by the crosses above.
    // The Zicbom and Zicbop read-backs are already implied by the existing base load crosses — no duplication needed.
    cp_pmlen_masking_read : cross priv_mode_m, pmm_active, pm_load_insn ;

    // cp_pmlen_disabled[]
    cp_pmlen_disabled_lw: cross priv_mode_m, pmm_disabled, lw_insn;
    cp_pmlen_disabled_sw: cross priv_mode_m, a_upper_bits, pmm_disabled, sw_insn;

    // cp_pmlen_misaligned[]
    // One misaligned store and one misaligned load, PMLEN=7 only, upper 7 bits = 0 or 1
    cp_pm_misaligned_word_write: cross priv_mode_m, pm_misalign_write;
    cp_pm_misaligned_word_read:  cross priv_mode_m, pm_misalign_read;

    `ifdef S_SUPPORTED  //As MXR is read-only zero if S mode is not supported
        // cp_pmm_mxr_addr_mode_write
        cp_pmm_mxr_addr_mode_write_pmm_active_mxr: cross priv_mode_m, pmm_active,   mxr_bit, a_upper_bits, sw_insn;
        // cp_pmm_mxr_addr_mode_read
        cp_pmm_mxr_addr_mode_read_pmm_active_mxr:  cross priv_mode_m, pmm_active,   mxr_bit, lw_insn;
    `endif

    // cp_pmm_addr_mode_jalr
    cp_pmm_addr_mode_jalr_pmm_: cross priv_mode_m, pmm_active, a_upper_bits, jalr_insn, jalr_a_upper_bits_nonzero;

    // cp_hardware_csr_writes
    // Fault crosses confirm lw/sw executed in M-mode at the illegal address.
    // Trap crosses confirm mtval holds the correctly masked address after the fault.
    cp_hardware_csr_writes_read_fault:   cross priv_mode_u,pm_read_fault;
    cp_hardware_csr_writes_write_fault:  cross priv_mode_u, pm_write_fault;

    // PMM=11, Bare
    cp_hardware_csr_writes_read_pmm11_bare_trap:   cross priv_mode_m, mtval_upper_pmm11_bare, exception_occurred, lw_insn;
    cp_hardware_csr_writes_write_pmm11_bare_trap:  cross priv_mode_m, mtval_upper_pmm11_bare, exception_occurred, sw_insn;
    // PMM=10, Bare
    cp_hardware_csr_writes_read_pmm10_bare_trap:   cross priv_mode_m, mtval_upper_pmm10_bare, exception_occurred, lw_insn;
    cp_hardware_csr_writes_write_pmm10_bare_trap:  cross priv_mode_m, mtval_upper_pmm10_bare, exception_occurred, sw_insn;

    // =======================================================================
    // cp_pm_mprv_write / cp_pm_mprv_read
    // =======================================================================
    // MPRV=1 causes M-mode memory accesses to use MPP's pointer masking
    // settings. Store uses tagged address A; load from A_masked confirms alias.
    cp_pm_mprv_write: cross priv_mode_m, pmm_active, mprv_bit, mpp_field, satp_mode, a_upper_bits, sw_insn;
    cp_pm_mprv_read:  cross priv_mode_m, pmm_active, mprv_bit, mpp_field, satp_mode, lw_insn;

    // cp_pm_csr_software_access_write / cp_pm_csr_software_access_read
    // Pointer masking must NOT be applied to software CSR reads/writes.
    cp_pm_csr_software_access_write: cross priv_mode_m, pmm_active, csr_target, csr_write_insn;
    cp_pm_csr_software_access_read:  cross priv_mode_m, pmm_active, csr_target, csr_read_insn;

    endgroup

    function void smmpm_sample(int hart, int issue, ins_t ins);
        Smmpm_cg.sample(ins);
    endfunction

`endif  // XLEN64
