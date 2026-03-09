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

    // Uses ins.prev instead of ins.current because Sail tracer updates CSRs after instruction retirement, so .current shows
    // post-trap state. May revert to .current depending on implementation consensus
    mstatus_mie: coverpoint ins.prev.csr[12'h300][3]  {
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

    cp_user_mti:    cross priv_mode_u, mtvec_mode, mstatus_mie, mie_mtie_one, mip_mtip;
    cp_user_msi:    cross priv_mode_u, mtvec_mode, mstatus_mie, mie_msie_one,  mip_msip;
    cp_user_mei:    cross priv_mode_u, mtvec_mode, mstatus_mie, mie_meie_one,   mip_meip;
    cp_wfi:         cross priv_mode_u, wfi,        mstatus_mie, mstatus_tw, mie_mtie_one;
    cp_wfi_timeout: cross priv_mode_u, wfi,        mstatus_mie, mstatus_tw, mie_mtie_one;

endgroup

function void interruptsu_sample(int hart, int issue, ins_t ins);
    InterruptsU_cg.sample(ins);

    // $display("=== InterruptsU Debug ===");
    // $display("PC: %h Instr: %s", ins.current.pc_rdata, ins.current.disass);
    // $display("  mstatus.MIE=%b mstatus.TW=%b mode: %b, vector: %b",
    //             ins.prev.csr[12'h300][3], ins.current.csr[12'h300][21], {ins.prev.mode_virt, ins.prev.mode}, {ins.current.csr[12'h305][1:0]});
    // $display("  mie: MEIE=%b MTIE=%b MSIE=%b (full=%h)",
    //             ins.current.csr[12'h304][11], ins.current.csr[12'h304][7],
    //             ins.current.csr[12'h304][3], ins.current.csr[12'h304][15:0]);
    // $display("  mip: MEIP=%b MTIP=%b MSIP=%b (full=%h)",
    //             ins.current.csr[12'h344][11], ins.current.csr[12'h344][7],
    //             ins.current.csr[12'h344][3], ins.current.csr[12'h344]);
    // if (ins.current.trap)
    //     $display("  TRAP! mcause=%h", ins.current.csr[12'h342]);
    // $display("");
endfunction

