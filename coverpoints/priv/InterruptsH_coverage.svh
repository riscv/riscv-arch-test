///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Hypervisor interrupt tests executed in HS, VS, VU and U modes.
// Written: David_Harris@hmc.edu 25 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSH

// VS-level interrupt bits {VSEI, VSTI, VSSI} of an hvip, hip, hie or hideleg value
`define INTERRUPTSH_VS(v) {v[10], v[6], v[2]}

// Every coverpoint is sampled in HS-mode, the guest ones at the T-SBI call that enters the guest
covergroup InterruptsH_hs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    csrrs : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    // csrsi sstatus, SSTATUS_SIE
    set_sie : coverpoint ins.current.insn[31:20] iff (ins.current.insn ==? CSRSI && ins.current.insn[19:15] == 5'd2) {
        bins sstatus = {CSR_SSTATUS};
    }
    hvip : coverpoint ins.current.insn[31:20] {
        bins hvip = {CSR_HVIP};
    }
    hip : coverpoint ins.current.insn[31:20] {
        bins hip = {CSR_HIP};
    }
    hie : coverpoint ins.current.insn[31:20] {
        bins hie = {CSR_HIE};
    }
    hip_vsip : coverpoint ins.current.insn[31:20] {
        bins hip  = {CSR_HIP};
        bins vsip = {CSR_VSIP};
    }
    hie_vsie : coverpoint ins.current.insn[31:20] {
        bins hie  = {CSR_HIE};
        bins vsie = {CSR_VSIE};
    }
    vsie : coverpoint ins.current.insn[31:20] {
        bins vsie = {CSR_VSIE};
    }
    vsip : coverpoint ins.current.insn[31:20] {
        bins vsip = {CSR_VSIP};
    }
    hideleg : coverpoint ins.current.insn[31:20] {
        bins hideleg = {CSR_HIDELEG};
    }

    // Setup CSRs sampled before the instruction, with one bin per combination of the VS-level bits
    hideleg_vs  : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_HIDELEG]);
    hvip_vs     : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_HVIP]);
    hie_vs      : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_HIE]);
    hideleg_all : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_HIDELEG]) { bins all = {3'b111}; }
    hvip_all    : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_HVIP])    { bins all = {3'b111}; }
    hie_all     : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_HIE])     { bins all = {3'b111}; }
    hideleg_none : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_HIDELEG]) {
        bins none = {3'b000};
    }
    sstatus_sie : coverpoint ins.prev.csr[CSR_SSTATUS][1];
    sstatus_sie_one : coverpoint ins.prev.csr[CSR_SSTATUS][1] {
        bins one = {1};
    }
    hvip_write : coverpoint `INTERRUPTSH_VS(ins.current.rs1_val);
    ones_16 : coverpoint ins.current.rs1_val {
        bins ones = {16'hFFFF};
    }

    // Raise each VS-level interrupt through hvip with sstatus.SIE, hideleg and hie = 0/1
    hideleg_vseip : coverpoint ins.prev.csr[CSR_HIDELEG][10];
    hideleg_vstip : coverpoint ins.prev.csr[CSR_HIDELEG][6];
    hideleg_vssip : coverpoint ins.prev.csr[CSR_HIDELEG][2];
    hie_vseie : coverpoint ins.prev.csr[CSR_HIE][10];
    hie_vstie : coverpoint ins.prev.csr[CSR_HIE][6];
    hie_vssie : coverpoint ins.prev.csr[CSR_HIE][2];
    set_vseip : coverpoint ins.current.rs1_val {
        bins vseip = {'h400};
    }
    set_vstip : coverpoint ins.current.rs1_val {
        bins vstip = {'h40};
    }
    set_vssip : coverpoint ins.current.rs1_val {
        bins vssip = {'h4};
    }
    cp_trigger_vsei: cross priv_mode_hs, csrrs, hvip, set_vseip, sstatus_sie, hideleg_vseip, hie_vseie;
    cp_trigger_vsti: cross priv_mode_hs, csrrs, hvip, set_vstip, sstatus_sie, hideleg_vstip, hie_vstie;
    cp_trigger_vssi: cross priv_mode_hs, csrrs, hvip, set_vssip, sstatus_sie, hideleg_vssip, hie_vssie;

    // Write hip = 0xFFFF and 0: only VSSIP is writable
    hip_write : coverpoint ins.current.rs1_val {
        bins ones  = {16'hFFFF};
        bins zeros = {0};
    }
    cp_hip_write: cross priv_mode_hs, csrrw, hip, hip_write;

    // Each combination of pending VS-level interrupts with each combination of hie or hideleg
    cp_priority_en_vsi:    cross priv_mode_hs, csrrw, hvip, hvip_write, hie_vs, hideleg_none, sstatus_sie_one;
    cp_priority_deleg_vsi: cross priv_mode_hs, csrrw, hvip, hvip_write, hideleg_vs, hie_all, sstatus_sie_one;

    // A pending S-level interrupt, or none, with every VS-level interrupt pending and enabled
    sie_ones : coverpoint {ins.prev.csr[CSR_SIE][9], ins.prev.csr[CSR_SIE][5], ins.prev.csr[CSR_SIE][1]} {
        bins ones = {3'b111};
    }
    sip_s : coverpoint {ins.prev.csr[CSR_SIP][9], ins.prev.csr[CSR_SIP][5], ins.prev.csr[CSR_SIP][1]} {
        bins sei  = {3'b100};
        bins sti  = {3'b010};
        bins ssi  = {3'b001};
        bins none = {3'b000};
    }
    cp_priority_s: cross priv_mode_hs, set_sie, sip_s, sie_ones, hvip_all, hie_all, hideleg_none;

    // hie, hip, vsie and vsip through hideleg
    mie_vs_all : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_MIE]) {
        bins all = {3'b111};
    }
    cp_hie:           cross priv_mode_hs, csrr, hie_vsie, hideleg_vs, mie_vs_all;
    cp_hip:           cross priv_mode_hs, csrr, hip_vsip, hideleg_vs, hvip_all;
    cp_hideleg:       cross priv_mode_hs, csrrw, hideleg, ones_16;
    cp_vsie:          cross priv_mode_hs, csrr, vsie, hideleg_vs, hie_vs;
    cp_vsip:          cross priv_mode_hs, csrr, vsip, hideleg_vs, hvip_vs;
    cp_vsie_from_hie: cross priv_mode_hs, csrrw, vsie, ones_16, hideleg_vs;

    // hie.SGEIE is an alias of mie.SGEIE, which is read-only zero when GEILEN = 0
    `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_0
        mie_1444 : coverpoint ins.prev.csr[CSR_MIE][12:0] {
            bins sgei_vs = {13'h1444};
        }
        cp_hie_gilen: cross priv_mode_hs, csrr, hie, mie_1444;
    `endif

    // Each interrupt taken into HS-mode with htinst nonzero
    htinst_nonzero : coverpoint (ins.prev.csr[CSR_HTINST] != 0) {
        bins nonzero = {1};
    }
    int_enabled : coverpoint (ins.prev.csr[CSR_SIE][13:0] | ins.prev.csr[CSR_HIE][13:0]) {
        bins ssi  = {14'h0002};
        bins vssi = {14'h0004};
        bins sti  = {14'h0020};
        bins vsti = {14'h0040};
        bins sei  = {14'h0200};
        bins vsei = {14'h0400};
        `ifdef SSCOFPMF_SUPPORTED
            bins lcofi = {14'h2000};
        `endif
    }
    cp_htinst: cross priv_mode_hs, set_sie, htinst_nonzero, int_enabled;

    // Guest external interrupts need the optional RVMODEL_SET_GUEST_EXT_INT hook
    `ifdef RVMODEL_SET_GUEST_EXT_INT
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
    `endif

    // The T-SBI calls that enter U, VS and VU mode: an ecall with a0 = TSBI_GOTO_UMODE (3), TSBI_GOTO_VSMODE (4)
    // or TSBI_GOTO_VUMODE (5), the function IDs of the T-SBI interface (CTP abstraction.adoc)
    ecall : coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    tsbi_goto_u : coverpoint ins.prev.x_wdata[10] {
        bins goto_u = {3};
    }
    tsbi_goto_vs : coverpoint ins.prev.x_wdata[10] {
        bins goto_vs = {4};
    }
    tsbi_goto_vu : coverpoint ins.prev.x_wdata[10] {
        bins goto_vu = {5};
    }
    vsstatus_sie : coverpoint ins.prev.csr[CSR_VSSTATUS][1];
    vsstatus_sie_one : coverpoint ins.prev.csr[CSR_VSSTATUS][1] {
        bins one = {1};
    }

    // Enter VS or VU mode with each combination of two of hideleg, hvip and hie, the third being 0x444
    cp_hideleg_hip_vs: cross priv_mode_hs, ecall, tsbi_goto_vs, hideleg_vs, hvip_vs, hie_all, vsstatus_sie_one;
    cp_hideleg_hie_vs: cross priv_mode_hs, ecall, tsbi_goto_vs, hideleg_vs, hvip_all, hie_vs, vsstatus_sie_one;
    cp_hip_hie_vs:     cross priv_mode_hs, ecall, tsbi_goto_vs, hideleg_all, hvip_vs, hie_vs, vsstatus_sie_one;
    cp_sie_vs:         cross priv_mode_hs, ecall, tsbi_goto_vs, hideleg_all, hvip_all, hie_all, vsstatus_sie;
    cp_hideleg_hip_vu: cross priv_mode_hs, ecall, tsbi_goto_vu, hideleg_vs, hvip_vs, hie_all;
    cp_hideleg_hie_vu: cross priv_mode_hs, ecall, tsbi_goto_vu, hideleg_vs, hvip_all, hie_vs;
    cp_hip_hie_vu:     cross priv_mode_hs, ecall, tsbi_goto_vu, hideleg_all, hvip_vs, hie_vs;

    // Enter VS-mode with a vectored vstvec and one delegated VS-level interrupt pending
    `ifdef UDB_VSTVEC_MODES_1
        vstvec_vectored : coverpoint ins.prev.csr[CSR_VSTVEC][1:0] {
            bins vect = {1};
        }
        hvip_one : coverpoint `INTERRUPTSH_VS(ins.prev.csr[CSR_HVIP]) {
            bins vsei = {3'b100};
            bins vsti = {3'b010};
            bins vssi = {3'b001};
        }
        cp_vsint_vectored: cross priv_mode_hs, ecall, tsbi_goto_vs, vstvec_vectored, hideleg_all, hvip_one,
                                 vsstatus_sie_one;
    `endif

    // Enter U-mode with the VS-level interrupts pending, enabled and delegated: none is taken
    cp_vsint_disabled_u: cross priv_mode_hs, ecall, tsbi_goto_u, hideleg_all, hvip_all, hie_all;
endgroup

function void interruptsh_sample(int hart, int issue, ins_t ins);
    InterruptsH_hs_cg.sample(ins);
endfunction
