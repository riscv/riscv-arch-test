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

`define COVER_ZAWRSSU
covergroup ZawrsSU_cg with function sample(ins_t ins);
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

    mstatus_sie: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        // autofill 0/1
    }
    mstatus_sie_zero: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        bins zero = {0};
    }
    mie_zeros: coverpoint ins.current.csr[CSR_MIE][15:0] {
        wildcard bins zeros = {16'b????0?0?0?0?0?0?}; // zero in all 6 interrupt enable bits
    }
    mie_mtie_one: coverpoint ins.current.csr[CSR_MIE][7] {
        bins one = {1}
    }

    hstatus_vtw_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")) {
        bins one = {1};
    }






    // main coverpoints
    cp_wrs_sto_timeout:     cross priv_mode_s_u, wrs_sto, mstatus_tw, mstatus_mie_zero,
                        `ifdef S_SUPPORTED
                            mstatus_sie_zero,
                        `endif
                            mie_zeros, lr_w;
    cp_wrs_no_res:          cross priv_mode_s_u, mstatus_tw, mstatus_mie_zero,
                        `ifdef S_SUPPORTED
                            mstatus_sie_zero,
                        `endif
                        mie_zeros, sc_w, wrs_ops;
    cp_wrs_resume:          cross priv_mode_s_u, mstatus_tw_zero, mie_mtie_one, mstatus_mie,
                        `ifdef S_SUPPORTED
                            mstatus_sie,
                        `endif
                        wrs_nto, lr_w;

    cp_wrs_nto_timeout:     cross priv_mode_s_u, mstatus_tw_one, mstatus_mie_zero,
                        `ifdef S_SUPPORTED
                            mstatus_sie_zero,
                        `endif
                        mie_zeros, wrs_nto, lr_w;

    // if H supported
    `ifdef H_SUPPORTED
        cp_wrs_nto_timeout_h:   cross priv_mode_vs_vu, mstatus_tw, mstatus_mie_zero,
                        `ifdef S_SUPPORTED
                            mstatus_sie_zero,
                        `endif
                        mie_zeros, hstatus_vtw_enabled, wrs_nto, lr_w;
    `endif


endgroup

// ---------------------
function void zawrssu_sample(int hart, int issue, ins_t ins);
    ZawrsSU_cg.sample(ins);
endfunction
