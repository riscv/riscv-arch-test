///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// SmnpmUSm — M-mode half of SmnpmU: pointer masking under MPRV with MPP=U, no S-mode.
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, SEP 2026), email: ammarahwakeel9@gmail.com
//
// Description:
//   With mstatus.MPRV=1 and MPP=U an M-mode load or store takes U-mode's effective
//   privilege. Without S-mode, menvcfg.PMM -- the CSR Smnpm adds -- governs U-mode, so
//   it decides how many upper bits are stripped, and mseccfg.PMM does not apply.
//   mseccfg.PMM is crossed in (when Smmpm is implemented) precisely to show that it is
//   ignored. MXR is read-only 0 and there is no satp without S-mode, so neither is crossed.
//
///////////////////////////////////////////

`define COVER_SMNPMUSM

    covergroup SmnpmUSm_cg with function sample(ins_t ins);
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

function void smnpmusm_sample(int hart, int issue, ins_t ins);
    SmnpmUSm_cg.sample(ins);
endfunction
