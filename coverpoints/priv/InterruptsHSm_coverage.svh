///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Hypervisor interrupt tests executed in M-mode.
// Written: David_Harris@hmc.edu 25 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSHSM

covergroup InterruptsHSm_m_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    ecall : coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    // csrsi mstatus, MSTATUS_MIE
    set_mie : coverpoint ins.current.insn[31:20] iff (ins.current.insn ==? CSRSI && ins.current.insn[19:15] == 5'd8) {
        bins mstatus = {CSR_MSTATUS};
    }
    write_zero : coverpoint ins.current.rs1_val {
        bins zero = {0};
    }
    hvip_all : coverpoint {ins.prev.csr[CSR_HVIP][10], ins.prev.csr[CSR_HVIP][6], ins.prev.csr[CSR_HVIP][2]} {
        bins all = {3'b111};
    }

    // mideleg bits 10, 6 and 2 (and 12 if GEILEN > 0) are read-only 1
    mideleg : coverpoint ins.current.insn[31:20] {
        bins mideleg = {CSR_MIDELEG};
    }
    cp_mideleg: cross priv_mode_m, csrrw, mideleg, write_zero;

    // mie and mip hold the hie and hip bits
    mie : coverpoint ins.current.insn[31:20] {
        bins mie = {CSR_MIE};
    }
    mip : coverpoint ins.current.insn[31:20] {
        bins mip = {CSR_MIP};
    }
    hie_vs : coverpoint ins.prev.csr[CSR_HIE][12:0] {
        bins vs = {13'h0444};
    }
    cp_mie: cross priv_mode_m, csrr, mie, hie_vs;
    cp_mip: cross priv_mode_m, csrr, mip, hvip_all;

    // hie.SGEIE is read-only zero when GEILEN = 0
    `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_0
        hie_sgei_vs : coverpoint ins.prev.csr[CSR_HIE][12:0] {
            bins sgei_vs = {13'h1444};
        }
        cp_mie_gilen: cross priv_mode_m, csrr, mie, hie_sgei_vs;
    `endif

    // VS-level interrupts pending and enabled in mie are not taken in M-mode
    mie_vs : coverpoint ins.prev.csr[CSR_MIE][12:0] {
        bins vs = {13'h0444};
    }
    hideleg_none : coverpoint {ins.prev.csr[CSR_HIDELEG][10], ins.prev.csr[CSR_HIDELEG][6], ins.prev.csr[CSR_HIDELEG][2]} {
        bins none = {3'b000};
    }
    cp_nohint_m: cross priv_mode_m, set_mie, mie_vs, hvip_all, hideleg_none;

    `ifdef RVMODEL_SET_GUEST_EXT_INT
        sgei_pending : coverpoint ((ins.prev.csr[CSR_HGEIP] & ins.prev.csr[CSR_HGEIE]) != 0) {
            bins pending = {1};
        }
        cp_mip_gilen: cross priv_mode_m, csrr, mip, sgei_pending;
    `endif

    // Enter VS or VU mode with one M-level or S-level interrupt pending and mideleg = 0 or 1s, sampled at the
    // T-SBI call: an ecall with a0 = TSBI_GOTO_VSMODE (4) or TSBI_GOTO_VUMODE (5) (CTP abstraction.adoc)
    tsbi_goto_vs : coverpoint ins.prev.x_wdata[10] {
        bins goto_vs = {4};
    }
    tsbi_goto_vu : coverpoint ins.prev.x_wdata[10] {
        bins goto_vu = {5};
    }
    mideleg_s : coverpoint {ins.prev.csr[CSR_MIDELEG][9], ins.prev.csr[CSR_MIDELEG][5], ins.prev.csr[CSR_MIDELEG][1]} {
        bins zeros = {3'b000};
        bins ones  = {3'b111};
    }
    mip_pending : coverpoint {ins.prev.csr[CSR_MIP][11], ins.prev.csr[CSR_MIP][9], ins.prev.csr[CSR_MIP][7],
                              ins.prev.csr[CSR_MIP][5], ins.prev.csr[CSR_MIP][3], ins.prev.csr[CSR_MIP][1]} {
        bins mei = {6'b100000};
        bins sei = {6'b010000};
        bins mti = {6'b001000};
        bins sti = {6'b000100};
        bins msi = {6'b000010};
        bins ssi = {6'b000001};
    }
    mie_ones : coverpoint {ins.prev.csr[CSR_MIE][11], ins.prev.csr[CSR_MIE][9], ins.prev.csr[CSR_MIE][7],
                           ins.prev.csr[CSR_MIE][5], ins.prev.csr[CSR_MIE][3], ins.prev.csr[CSR_MIE][1]} {
        bins ones = {6'b111111};
    }
    mstatus_mie_zero : coverpoint ins.prev.csr[CSR_MSTATUS][3] {
        bins zero = {0};
    }
    cp_mideleg_mip_vs: cross priv_mode_m, ecall, tsbi_goto_vs, mideleg_s, mip_pending, mie_ones, mstatus_mie_zero;
    cp_mideleg_mip_vu: cross priv_mode_m, ecall, tsbi_goto_vu, mideleg_s, mip_pending, mie_ones, mstatus_mie_zero;

    // Each interrupt taken into M-mode with mtinst nonzero
    mtinst_nonzero : coverpoint (ins.prev.csr[CSR_MTINST] != 0) {
        bins nonzero = {1};
    }
    int_enabled : coverpoint ins.prev.csr[CSR_MIE][13:0] {
        bins ssi = {14'h0002};
        bins msi = {14'h0008};
        bins sti = {14'h0020};
        bins mti = {14'h0080};
        bins sei = {14'h0200};
        bins mei = {14'h0800};
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofi = {14'h2000};
        `endif
    }
    cp_mtinst: cross priv_mode_m, set_mie, mtinst_nonzero, int_enabled;
endgroup

function void interruptshsm_sample(int hart, int issue, ins_t ins);
    InterruptsHSm_m_cg.sample(ins);
endfunction
