///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Ellen Yu ellyu@hmc.edu June 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZAWRS
covergroup Zawrs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    wrs_nto: coverpoint ins.current.insn {
        bins wrs_nto = {WRS_NTO};
    }

    wrs_sto: coverpoint ins.current.insn {
        bins wrs_nto = {WRS_STO};
    }

    mstatus_tw:  coverpoint ins.current.csr[CSR_MSTATUS][21] {
        // autofill 0/1
    }

    mstatus_tw_one:  coverpoint ins.current.csr[CSR_MSTATUS][21] {
        bins one = {1};
    }

    mstatus_tw_zero:  coverpoint ins.current.csr[CSR_MSTATUS][21] {
        bins zero = {0};
    }

    mip_mtip_one: coverpoint ins.current.csr[CSR_MIP][7] {
        bins one = {1};
    }



    // main coverpoints
    cp_wrs_sto_timeout_m:     cross priv_mode_m, wrs_sto, mstatus_tw_zero,

endgroup

// ---------------------
function void zawrs_sample(int hart, int issue, ins_t ins);
    Zawrs_cg.sample(ins);
endfunction
