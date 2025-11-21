///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu, Jordan Carlin jcarlin@hmc.edu 08 Feb 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSM

covergroup InterruptsM_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    mstatus_mie_one: coverpoint ins.current.csr[12'h300][3] {
        bins one = {1};
    }
    mstatus_mie: coverpoint ins.current.csr[12'h300][3]  {
        // autofill 0/1
    }
    mstatus_tw:  coverpoint ins.current.csr[12'h300][21] {
        // autofill 0/1
    }
    mie_mtie_one: coverpoint ins.current.csr[12'h304][7] {
        bins one = {1};
    }
    mie_ones: coverpoint ins.current.csr[12'h304][15:0] {
        wildcard bins ones = {16'b????1???1???1???}; // ones in all machine interrupt enable bits
    }
    mip_msip_one: coverpoint ins.current.csr[12'h344][3] {
        bins one = {1};
    }
    mip_mtip: coverpoint ins.current.csr[12'h344][7] {
        // autofill 0/1
    }
    mie_mtip_one: coverpoint ins.current.csr[12'h344][7] {
        bins one = {1};
    }
    mip_mtip_one: coverpoint ins.current.csr[12'h344][7] {
        bins one = {1};
    }
    mip_meip_one: coverpoint ins.current.csr[12'h344][11] {
        bins one = {1};
    }
    mie_walking: coverpoint {ins.current.csr[12'h304][11],
                             ins.current.csr[12'h304][7],
                             ins.current.csr[12'h304][3] } {
        bins meie = {3'b001};
        bins mtie = {3'b010};
        bins msie = {3'b100};
    }
    mip_walking: coverpoint {ins.current.csr[12'h344][11],
                             ins.current.csr[12'h344][7],
                             ins.current.csr[12'h344][3] } {
        bins meip = {3'b001};
        bins mtip = {3'b010};
        bins msip = {3'b100};
    }
    mie_meie_mtie_msie: coverpoint {ins.current.csr[12'h304][11],
                                    ins.current.csr[12'h304][7],
                                    ins.current.csr[12'h304][3] } {
        // auto fills all 8 combinations
    }
    mip_meip_mtip_msip: coverpoint {ins.current.csr[12'h344][11],
                                    ins.current.csr[12'h344][7],
                                    ins.current.csr[12'h344][3] } {
        // auto fills all 8 combinations
    }
    mtvec_direct: coverpoint ins.current.csr[12'h305][1:0] {
        bins direct   = {2'b00};
    }
    mtvec_vectored: coverpoint ins.current.csr[12'h305][1:0] {
        bins vector   = {2'b01};
    }
    wfi: coverpoint ins.current.insn {
        bins wfi = {32'b0001000_00101_00000_000_00000_1110011};
    }
    // m_ext_intr: coverpoint ins.current.m_ext_intr {
    //     bins mei = {1};
    // }
    // m_timer_intr: coverpoint ins.current.m_timer_intr {
    //     bins mti = {1};
    // }
    // m_soft_intr: coverpoint ins.current.m_soft_intr {
    //     bins msi = {1};
    // }

    // main coverpoints

    cp_trigger_mti:      cross priv_mode_m, mstatus_mie, mie_ones, mip_mtip_one;
    cp_trigger_msi:      cross priv_mode_m, mstatus_mie, mie_ones, mip_msip_one;
    cp_trigger_mei:      cross priv_mode_m, mstatus_mie, mie_ones, mip_meip_one;
    cp_interrupts:       cross priv_mode_m, mstatus_mie, mtvec_direct, mip_walking, mie_walking;
    cp_vectored:         cross priv_mode_m, mstatus_mie_one, mtvec_vectored, mip_walking, mie_ones;
    cp_priority:         cross priv_mode_m, mstatus_mie_one, mie_meie_mtie_msie, mip_meip_mtip_msip;
    cp_wfi:              cross priv_mode_m, wfi, mstatus_mie, mstatus_tw, mie_mtie_one, mie_mtip_one;
endgroup

function void interruptsm_sample(int hart, int issue, ins_t ins);
    InterruptsM_cg.sample(ins);
endfunction
