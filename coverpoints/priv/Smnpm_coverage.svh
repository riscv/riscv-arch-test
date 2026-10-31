///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Smnpm — Machine-mode pointer masking for next lower privilege.
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
// Written: Ammarah Wakeel (UET LHR, SEP 2026), email: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
//
// Groups:
//   S    — S-mode accesses across all supported satp modes
//   SSm  — M-mode half of S: MPRV=1 with MPP=S
//   U    — U-mode accesses when S-mode is not present
//   USm  — M-mode half of U: MPRV=1 with MPP=U, no S-mode
//
// Description:
//   Covers menvcfg.PMM configuration (PMM=00/10/11 → PMLEN=0/7/16) in M-mode
//   and its effect on lower-privilege memory accesses.
//   When PMM is active, hardware strips the upper PMLEN bits of the effective
//   address before the access reaches PMP/MMU, so a tagged address A and its
//   masked form alias to the same physical location.
//
//       PMM = 00 → PMLEN =  0  (masking disabled)
//       PMM = 10 → PMLEN =  7  (upper  7 bits ignored, bits [63:57])
//       PMM = 11 → PMLEN = 16  (upper 16 bits masked, bits [63:48])
//
///////////////////////////////////////////
`define COVER_SMNPM

// Smnpm applies to S mode when S is implemented
`ifdef S_SUPPORTED

covergroup Smnpm_S_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        `ifdef UDB_SUPPORTED_PMLEN_SMNPM_7
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SMNPM_16
            bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
        `endif
    }

    //Declare pmm before including the shared PMM coverpoint file so the include can reference it.
    `include "general/RISCV_coverage_pmm_coverpoints.svh"

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
        bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
        bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
    }
    csr_target: coverpoint ins.current.insn[31:20] { //excluding read-only csrs
        bins sepc     = {CSR_SEPC};
        //bins stvec    = {CSR_STVEC}; //// warl field has complex write restrictions and is not easy to test
        bins sscratch = {CSR_SSCRATCH};
    }

    // Main Crosses
    cp_pmlen_masking : cross priv_mode_s, pmm, satp_mode, a_upper_bits, pm_insn;
    `ifdef ZICFISS_SUPPORTED
        cp_pmlen_zicfiss_amo : cross priv_mode_s, pmm, satp_mode_zicfiss, a_upper_bits, pm_ssamoswap_insn;
        cp_pmlen_zicfiss_ssp : cross priv_mode_s, pmm, satp_mode_zicfiss, ssp_upper_bits, pm_ssp_insn;
    `endif // ZICFISS_SUPPORTED
    cp_pmlen_misaligned_word: cross priv_mode_s, satp_mode, pmm, a_upper_bits, sw_lw_insn, misaligned_addr;
    cp_pmm_mxr: cross priv_mode_s, pmm, mxr_bit, satp_mode, a_upper_bits, sw_lw_insn;
    cp_pmm_jalr: cross priv_mode_s, pmm, mxr_bit, satp_mode, a_upper_bits, jalr_insn;
    cp_pm_csr_software_access: cross priv_mode_s, pmm, csr_target, csrw_insn;

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Fault crosses confirm lw/sw executed in S-mode at the illegal address.
        cp_hardware_csr_writes_fault: cross priv_mode_s, satp_mode, pmm, a_upper_bits, sw_lw_insn, illegal_addr;
    `endif
endgroup

`ifndef EXCLUDE_SM
covergroup Smnpm_SSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        `ifdef UDB_SUPPORTED_PMLEN_SMNPM_7
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SMNPM_16
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

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
        bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
    }
    mprv_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins mprv_1 = {1'b1};   // MPRV=1: memory access uses MPP privilege
    }
    mpp_field_s: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        bins mpp_s = {2'b01};   // effective privilege = S-mode
    }

    // Main Cross
    `ifdef SMMPM_SUPPORTED
        cp_pm_mprv_mpp_s: cross priv_mode_m, pmm, mseccfg_pmm, mprv_bit, mxr_bit, satp_mode_mprv, a_upper_bits_mprv, sw_lw_insn, mpp_field_s;
    `else
        cp_pm_mprv_mpp_s: cross priv_mode_m, pmm, mprv_bit, mxr_bit, satp_mode_mprv, a_upper_bits_mprv, sw_lw_insn, mpp_field_s;
    `endif // SMMPM_SUPPORTED
endgroup
`endif // EXCLUDE_SM

`else // S not supported, Smnpm applies to U mode
covergroup Smnpm_U_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        `ifdef UDB_SUPPORTED_PMLEN_SMNPM_7
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SMNPM_16
            bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
        `endif
    }

    //Declare pmm before including the shared PMM coverpoint file so the include can reference it.
    `include "general/RISCV_coverage_pmm_coverpoints.svh"

    // Main Crosses
    cp_pmlen_masking : cross priv_mode_u, pmm, a_upper_bits, pm_insn;
    cp_pmlen_misaligned_word: cross priv_mode_u, pmm, a_upper_bits, sw_lw_insn, misaligned_addr;
    cp_pmm_jalr: cross priv_mode_u, pmm, a_upper_bits, jalr_insn;

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Fault crosses confirm lw/sw executed in U-mode at the illegal address.
        cp_hardware_csr_writes_fault: cross priv_mode_u, pmm, a_upper_bits, sw_lw_insn, illegal_addr;
    `endif
endgroup

`ifndef EXCLUDE_SM
covergroup Smnpm_USm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
        bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
        `ifdef UDB_SUPPORTED_PMLEN_SMNPM_7
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
        `endif
        `ifdef UDB_SUPPORTED_PMLEN_SMNPM_16
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

    mprv_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins mprv_1 = {1'b1};   // MPRV=1: memory access uses MPP privilege
    }
    mpp_field_u: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        bins mpp_u = {2'b00};   // effective privilege = U-mode
    }

    // Main Cross
    `ifdef SMMPM_SUPPORTED
        cp_pm_mprv_mpp_u: cross priv_mode_m, pmm, mseccfg_pmm, mprv_bit, a_upper_bits_mprv, sw_lw_insn, mpp_field_u;
    `else
        cp_pm_mprv_mpp_u: cross priv_mode_m, pmm, mprv_bit, a_upper_bits_mprv, sw_lw_insn, mpp_field_u;
    `endif // SMMPM_SUPPORTED
endgroup

`endif // EXCLUDE_SM
`endif // S_SUPPORTED

function void smnpm_sample(int hart, int issue, ins_t ins);
// Smnpm applies to S mode when S is implemented
`ifdef S_SUPPORTED
    Smnpm_S_cg.sample(ins);
    `ifndef EXCLUDE_SM
        Smnpm_SSm_cg.sample(ins);
    `endif // EXCLUDE_SM
`else // S not supported, Smnpm applies to U mode
    Smnpm_U_cg.sample(ins);
    `ifndef EXCLUDE_SM
        Smnpm_USm_cg.sample(ins);
    `endif // EXCLUDE_SM
`endif // S_SUPPORTED
endfunction
