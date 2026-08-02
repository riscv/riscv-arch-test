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

`define COVER_SMNPMS

    covergroup SmnpmS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
    }

    //Declare pmm before including the shared PMM coverpoint file so the include can reference it.
    `include "general/RISCV_coverage_pmm_coverpoints.svh"

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
        bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
    }
    `ifndef UDB_SXLEN_64
        sxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sxl") {
            bins sxl_01 = {2'b01};
        }
    `endif // UDB_SXLEN_64
    csr_target: coverpoint ins.current.insn[31:20] { //excluding read-only csrs
        bins sepc     = {CSR_SEPC};
        //bins stvec    = {CSR_STVEC}; //// warl field has complex write restrictions and is not easy to test
        bins sscratch = {CSR_SSCRATCH};
    }

    // Main Crosses
    cp_pmlen_masking : cross priv_mode_s, pmm, satp_mode, a_upper_bits, pm_insn;
    cp_pmlen_misaligned_word: cross priv_mode_s, satp_mode, pm_misalign;
    cp_pmm_mxr: cross priv_mode_s, pmm, mxr_bit, satp_mode, a_upper_bits, sw_lw_insn;
    cp_pmm_jalr: cross priv_mode_s, pmm, mxr_bit, satp_mode, a_upper_bits, jalr_insn;
    `ifndef UDB_SXLEN_64
        cp_pmm_sxl_clear: cross pmm, sxl_rv32;
    `endif // UDB_SXLEN_64
    cp_pm_csr_software_access: cross priv_mode_s, pmm, csr_target, csrw_insn;

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Fault crosses confirm lw/sw executed in S-mode at the illegal address.
        cp_hardware_csr_writes_fault: cross priv_mode_s, satp_mode, pm_fault;
    `endif

endgroup

function void smnpms_sample(int hart, int issue, ins_t ins);
    SmnpmS_cg.sample(ins);
endfunction
