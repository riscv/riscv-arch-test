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
//   are always forced to zero.
//
//       PMM = 00 → PMLEN =  0  (masking disabled)
//       PMM = 10 → PMLEN =  7  (upper  7 bits ignored, bits [63:57])
//       PMM = 11 → PMLEN = 16  (upper 16 bits masked, bits [63:48])
///////////////////////////////////////////


`define COVER_SMMPM

    covergroup Smmpm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mseccfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
    }

    //Declare pmm before including the shared PMM coverpoint file so the include can reference it.
    `include "general/RISCV_coverage_pmm_coverpoints.svh"

    `ifdef S_SUPPORTED  //As MXR is read-only zero if S mode is not supported
        mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
            bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
            bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
        }
    `endif

    mprv_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins mprv_1 = {1'b1};   // MPRV=1: memory access uses MPP privilege
    }
    mpp_field: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        `ifdef U_SUPPORTED
            bins mpp_u = {2'b00};   // effective privilege = U-mode
        `endif
        `ifdef S_SUPPORTED
            bins mpp_s = {2'b01};   // effective privilege = S-mode
        `endif
    }
    csr_target: coverpoint ins.current.insn[31:20] { //excluding read-only csrs
        bins mepc     = {CSR_MEPC};
        //bins mtvec    = {CSR_MTVEC}; //// warl field has complex write restrictions and is not easy to test
        bins mscratch = {CSR_MSCRATCH};
    }

    //Main Crosses
    cp_pmlen_masking : cross priv_mode_m, pmm, a_upper_bits, pm_insn;
    cp_pmlen_misaligned_word: cross priv_mode_m, pm_misalign;
    cp_pm_csr_software_access: cross priv_mode_m, pmm, csr_target, csrw_insn;

    // MPRV=1 causes M-mode memory accesses to use MPP's pointer masking
    cp_pm_mprv: cross priv_mode_m, pmm, mprv_bit, mpp_field, satp_mode, a_upper_bits, sw_lw_insn;

    // cp_pmm_addr_mode_jalr — not guarded by S_SUPPORTED; implicit fetch is
    // never pointer-masked regardless of PMM or MXR availability.
    cp_pmm_jalr: cross priv_mode_m, pmm, a_upper_bits, jalr_insn;

    `ifdef S_SUPPORTED  //As MXR is read-only zero if S mode is not supported
        cp_pmm_mxr: cross priv_mode_m, pmm, mxr_bit, a_upper_bits, sw_lw_insn;
    `endif

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Fault crosses confirm lw/sw executed in M-mode at the illegal address.
        cp_hardware_csr_writes_fault: cross priv_mode_m, pm_fault;
    `endif

endgroup

function void smmpm_sample(int hart, int issue, ins_t ins);
    Smmpm_cg.sample(ins);
endfunction
