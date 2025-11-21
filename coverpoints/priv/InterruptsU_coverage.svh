///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 16 Feb 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSU
covergroup InterruptsU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    mstatus_sie: coverpoint ins.current.csr[12'h300][1]  {
        // autofill 0/1
    }
    mstatus_mie: coverpoint ins.current.csr[12'h300][3]  {
        // autofill 0/1
    }
    mstatus_tw:  coverpoint ins.current.csr[12'h300][21] {
        // autofill 0/1
    }
    mideleg_ones_zeros: coverpoint ins.current.csr[12'h303] {
        wildcard bins ones  = {16'b????1???1???1???}; //  ones in every field that is not tied to zero
        wildcard bins zeros = {16'b????0???0???0???}; // zeros in every field that is not tied to zero
    }
    mie_msie_one: coverpoint ins.current.csr[12'h304][3] {
        bins one = {1};
    }
    mie_mtie_one: coverpoint ins.current.csr[12'h304][7] {
        bins one = {1};
    }
    mie_meie_one: coverpoint ins.current.csr[12'h304][11] {
        bins one = {1};
    }
    mtvec_mode: coverpoint ins.current.csr[12'h305][1:0] {
        bins direct   = {2'b00};
        bins vector   = {2'b01};
    }
    mip_msip:    coverpoint ins.current.csr[12'h344][3]  {
        // autofill 0/1
    }
    mip_mtip:    coverpoint ins.current.csr[12'h344][7]  {
        // autofill 0/1
    }
    mip_meip:    coverpoint ins.current.csr[12'h344][11] {
        // autofill 0/1
    }
    wfi: coverpoint ins.current.insn {
        bins wfi = {32'b0001000_00101_00000_000_00000_1110011};
    }
    timeout: coverpoint ins.current.csr[12'h344][7] iff (ins.trap == 1) {
        bins no_timer_int = {0};
    }
    m_ext_intr: coverpoint ins.current.m_ext_intr {
        bins mei = {1};
    }
    m_timer_intr: coverpoint ins.current.m_timer_intr {
        bins mti = {1};
    }
    m_soft_intr: coverpoint ins.current.m_soft_intr {
        bins msi = {1};
    }

    // main coverpoints
    cp_user_mti:    cross priv_mode_u, mtvec_mode, mstatus_mie, mie_mtie_one, m_timer_intr, mip_mtip;
    cp_user_msi:    cross priv_mode_u, mtvec_mode, mstatus_mie, mie_msie_one, m_soft_intr,  mip_msip;
    cp_user_mei:    cross priv_mode_u, mtvec_mode, mstatus_mie, mie_meie_one, m_ext_intr,   mip_meip;
    cp_wfi:         cross priv_mode_u, wfi,        mstatus_mie, mstatus_tw, mie_mtie_one, m_timer_intr;
    cp_wfi_timeout: cross priv_mode_u, wfi,        mstatus_mie, mstatus_tw, mie_mtie_one, timeout;

endgroup

function void interruptsu_sample(int hart, int issue, ins_t ins);
    InterruptsU_cg.sample(ins);
endfunction
