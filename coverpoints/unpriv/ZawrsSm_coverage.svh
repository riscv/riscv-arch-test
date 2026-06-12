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

`define COVER_ZAWRSSM
covergroup ZawrsSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    wrs_nto: coverpoint ins.current.insn {
        bins wrs_nto = {WRS_NTO};
    }

    wrs_sto: coverpoint ins.current.insn {
        bins wrs_sto = {WRS_STO};
    }

    wrs_ops: coverpoint ins.current.insn {
        bins wrs_nto = {WRS_NTO};
        bins wrs_sto = {WRS_STO};

    }

    sc_w: coverpoint ins.prev.insn {
        wildcard bins sc_w = {SC_W};
    }
    lr_w: coverpoint ins.prev.insn {
        wildcard bins lr_w = {LR_W};
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

    mstatus_mie: coverpoint ins.prev.csr[CSR_MSTATUS][3]  {
        // autofill 0/1
    }
    mstatus_mie_zero: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
        bins zero = {0};
    }
    mstatus_mie_one: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
        bins one = {1};
    }

    mip_mtip_one: coverpoint ins.current.csr[CSR_MIP][7] {
        bins one = {1};
    }

    mie_zeros: coverpoint ins.current.csr[CSR_MIE][15:0] {
        wildcard bins zeros = {16'b????0?0?0?0?0?0?}; // zero in all 6 interrupt enable bits
    }
    mie_mtie_one: coverpoint ins.current.csr[CSR_MIE][7] {
        bins one = {1}
    }



    // main coverpoints
    cp_wrs_sto_timeout:     cross priv_mode_m, wrs_sto, mstatus_tw, mstatus_mie_zero, mie_zeros, lr_w;
    cp_wrs_no_res:          cross priv_mode_m, mstatus_tw, mstatus_mie_zero, mie_zeros, sc_w, wrs_ops;
    cp_wrs_resume:          cross priv_mode_m, mstatus_tw_zero, mie_mtie_one, mstatus_mie, wrs_nto, lr_w;


endgroup

// ---------------------
function void zawrssm_sample(int hart, int issue, ins_t ins);
    ZawrsSm_cg.sample(ins);
endfunction
