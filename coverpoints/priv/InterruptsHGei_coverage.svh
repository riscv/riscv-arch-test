///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Guest external interrupt tests, which need the platform to raise hgeip bits.
// Written: David_Harris@hmc.edu 25 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSHGEI

// Guest external interrupts need the optional RVMODEL_SET_GUEST_EXT_INT hook; without it the covergroups are empty
`ifdef RVMODEL_SET_GUEST_EXT_INT

// Read mip from M-mode with a guest external interrupt pending
covergroup InterruptsHGei_m_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    mip : coverpoint ins.current.insn[31:20] {
        bins mip = {CSR_MIP};
    }
    sgei_pending : coverpoint ((ins.prev.csr[CSR_HGEIP] & ins.prev.csr[CSR_HGEIE]) != 0) {
        bins pending = {1};
    }
    cp_mip_gilen: cross priv_mode_m, csrr, mip, sgei_pending;
endgroup

// hgeip, hgeie, hip.SGEIP, hstatus.VGEIN and the SGEI priority, sampled in HS-mode
covergroup InterruptsHGei_hs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    // csrsi sstatus, SSTATUS_SIE
    set_sie : coverpoint ins.current.insn[31:20] iff (ins.current.insn ==? CSRSI && ins.current.insn[19:15] == 5'd2) {
        bins sstatus = {CSR_SSTATUS};
    }
    hip : coverpoint ins.current.insn[31:20] {
        bins hip = {CSR_HIP};
    }
    hie : coverpoint ins.current.insn[31:20] {
        bins hie = {CSR_HIE};
    }
    sstatus_sie : coverpoint ins.prev.csr[CSR_SSTATUS][1];
    hvip_all : coverpoint {ins.prev.csr[CSR_HVIP][10], ins.prev.csr[CSR_HVIP][6], ins.prev.csr[CSR_HVIP][2]} {
        bins all = {3'b111};
    }
    hideleg_none : coverpoint {ins.prev.csr[CSR_HIDELEG][10], ins.prev.csr[CSR_HIDELEG][6], ins.prev.csr[CSR_HIDELEG][2]} {
        bins none = {3'b000};
    }
    sie_ones : coverpoint {ins.prev.csr[CSR_SIE][9], ins.prev.csr[CSR_SIE][5], ins.prev.csr[CSR_SIE][1]} {
        bins ones = {3'b111};
    }

    sgei_pending : coverpoint ((ins.prev.csr[CSR_HGEIP] & ins.prev.csr[CSR_HGEIE]) != 0) {
        bins pending = {1};
    }
    hie_write_sgeie : coverpoint ins.current.rs1_val[12];
    hie_1444 : coverpoint ins.prev.csr[CSR_HIE][12:0] {
        bins sgei_vs = {13'h1444};
    }
    sip_s_pending : coverpoint {ins.prev.csr[CSR_SIP][9], ins.prev.csr[CSR_SIP][5], ins.prev.csr[CSR_SIP][1]} {
        bins sei  = {3'b100};
        bins sti  = {3'b010};
        bins ssi  = {3'b001};
    }
    sip_s_none : coverpoint {ins.prev.csr[CSR_SIP][9], ins.prev.csr[CSR_SIP][5], ins.prev.csr[CSR_SIP][1]} {
        bins none = {3'b000};
    }
    cp_trigger_sgei:    cross priv_mode_hs, csrrw, hie, hie_write_sgeie, sstatus_sie, sgei_pending;
    cp_priority_sgei:   cross priv_mode_hs, set_sie, sgei_pending, hie_1444, sie_ones, sip_s_none, hvip_all,
                              hideleg_none;
    cp_priority_sgei_s: cross priv_mode_hs, set_sie, sgei_pending, hie_1444, sie_ones, sip_s_pending, hvip_all,
                              hideleg_none;

    // Each guest external interrupt i enabled alone, with hgeip = 0, bit i or every implemented bit
    hgeie_bit : coverpoint $clog2(ins.prev.csr[CSR_HGEIE]) iff ($onehot(ins.prev.csr[CSR_HGEIE])) {
        bins b[] = {[1:`UDB_NUM_EXTERNAL_GUEST_INTERRUPTS]};
    }
    hgeip_vs_hgeie : coverpoint (ins.prev.csr[CSR_HGEIP] == 0 ? 0 : ins.prev.csr[CSR_HGEIP] == ins.prev.csr[CSR_HGEIE] ? 1 : 2) {
        bins none = {0};
        bins i    = {1};
        bins all  = {2};
    }
    cp_hgeie: cross priv_mode_hs, csrr, hip, hgeie_bit, hgeip_vs_hgeie;

    // hstatus.VGEIN = i selects hgeip bit i into hip.VSEIP, whatever hgeie holds
    vgein : coverpoint ins.prev.csr[CSR_HSTATUS][17:12] {
        bins b[] = {[1:`UDB_NUM_EXTERNAL_GUEST_INTERRUPTS]};
    }
    vgein_zero : coverpoint ins.prev.csr[CSR_HSTATUS][17:12] {
        bins zero = {0};
    }
    hgeip_vs_vgein : coverpoint (ins.prev.csr[CSR_HGEIP] == 0 ? 0 :
                                 ins.prev.csr[CSR_HGEIP] == (1 << ins.prev.csr[CSR_HSTATUS][17:12]) ? 1 :
                                 ins.prev.csr[CSR_HGEIP][ins.prev.csr[CSR_HSTATUS][17:12]] ? 3 : 2) {
        bins none   = {0};
        bins i      = {1};
        bins others = {2};
    }
    hgeie_vgein : coverpoint ins.prev.csr[CSR_HGEIE][ins.prev.csr[CSR_HSTATUS][17:12]];
    hgeip_nonzero : coverpoint (ins.prev.csr[CSR_HGEIP] != 0) {
        bins nonzero = {1};
    }
    cp_trigger_vsei_hgeip: cross priv_mode_hs, csrr, hip, vgein, hgeip_vs_vgein, hgeie_vgein;
    cp_hgeip0:             cross priv_mode_hs, csrr, hip, vgein_zero, hgeip_nonzero, sgei_pending;
endgroup

`endif // RVMODEL_SET_GUEST_EXT_INT

function void interruptshgei_sample(int hart, int issue, ins_t ins);
    `ifdef RVMODEL_SET_GUEST_EXT_INT
        InterruptsHGei_m_cg.sample(ins);
        InterruptsHGei_hs_cg.sample(ins);
    `endif
endfunction
