///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Smcntrpmf privilege mode filtering of cycle and instret in VS-mode and VU-mode.
// Written: David_Harris@hmc.edu 29 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SMCNTRPMFH

// {MINH, SINH, UINH, VSINH, VUINH} of mcyclecfg or minstretcfg (bits 63:32, in the upper-half CSR on RV32)
`define SMCNTRPMFH_INH(CSR) {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR, "minh")[0], \
                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR, "sinh")[0], \
                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR, "uinh")[0], \
                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR, "vsinh")[0], \
                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR, "vuinh")[0]}
`ifdef UDB_MXLEN_64
    `define SMCNTRPMFH_MCYCLECFG "mcyclecfg"
    `define SMCNTRPMFH_MINSTRETCFG "minstretcfg"
`else
    `define SMCNTRPMFH_MCYCLECFG "mcyclecfgh"
    `define SMCNTRPMFH_MINSTRETCFG "minstretcfgh"
`endif

covergroup SmcntrpmfH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // Every mode inhibited, or every mode but VS or VU
    mcyclecfg_vs: coverpoint `SMCNTRPMFH_INH(`SMCNTRPMFH_MCYCLECFG) {
        bins inhibit_all   = {5'b11111};
        bins count_only_vs = {5'b11101};
    }
    mcyclecfg_vu: coverpoint `SMCNTRPMFH_INH(`SMCNTRPMFH_MCYCLECFG) {
        bins inhibit_all   = {5'b11111};
        bins count_only_vu = {5'b11110};
    }
    minstretcfg_vs: coverpoint `SMCNTRPMFH_INH(`SMCNTRPMFH_MINSTRETCFG) {
        bins inhibit_all   = {5'b11111};
        bins count_only_vs = {5'b11101};
    }
    minstretcfg_vu: coverpoint `SMCNTRPMFH_INH(`SMCNTRPMFH_MINSTRETCFG) {
        bins inhibit_all   = {5'b11111};
        bins count_only_vu = {5'b11110};
    }

    // An instruction executed in VS or VU while the counter is inhibited or counts only there
    cp_mcyclecfg_vs: cross priv_mode_vs, mcyclecfg_vs;
    cp_mcyclecfg_vu: cross priv_mode_vu, mcyclecfg_vu;
    cp_minstretcfg_vs: cross priv_mode_vs, minstretcfg_vs;
    cp_minstretcfg_vu: cross priv_mode_vu, minstretcfg_vu;
endgroup

function void smcntrpmfh_sample(int hart, int issue, ins_t ins);
    SmcntrpmfH_cg.sample(ins);
endfunction
