///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// InterruptsH: hstatus.VGEIN switching and the VS-level interrupt aliases.
// Written: David_Harris@hmc.edu 8 November 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSH

covergroup InterruptsH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // hip.VSEIP follows hgeip[VGEIN] after every write of hstatus.VGEIN
    hstatus_csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW} iff (ins.current.insn[31:20] == CSR_HSTATUS);
    }
    hstatus_csrrs : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS} iff (ins.current.insn[31:20] == CSR_HSTATUS);
    }
    hstatus_csrrc : coverpoint ins.current.insn {
        wildcard bins csrrc = {CSRRC} iff (ins.current.insn[31:20] == CSR_HSTATUS);
    }
    // {old VGEIN == 0, hgeip[old VGEIN], new VGEIN == 0, hgeip[new VGEIN]}; hgeip[0] reads 0.  csrrs cannot reach
    // VGEIN = 0 and csrrc cannot leave it, so each form has its own coverpoint with the transitions it can make.
    vgein_switch_rw : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS)[17:12] == 0,
                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGEIP)[get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS)[17:12]],
                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HSTATUS)[17:12] == 0,
                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HGEIP)[get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HSTATUS)[17:12]]} {
        bins pending_to_zero = {4'b0110};
        bins pending_to_idle = {4'b0100};
        bins zero_to_pending = {4'b1001};
        bins idle_to_pending = {4'b0001};
    }
    vgein_switch_set : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS)[17:12] == 0,
                                   get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGEIP)[get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS)[17:12]],
                                   get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HSTATUS)[17:12] == 0,
                                   get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HGEIP)[get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HSTATUS)[17:12]]} {
        bins pending_to_idle = {4'b0100};
        bins zero_to_pending = {4'b1001};
        bins idle_to_pending = {4'b0001};
    }
    vgein_switch_clear : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS)[17:12] == 0,
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HGEIP)[get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HSTATUS)[17:12]],
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HSTATUS)[17:12] == 0,
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HGEIP)[get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_HSTATUS)[17:12]]} {
        bins pending_to_zero = {4'b0110};
        bins pending_to_idle = {4'b0100};
        bins idle_to_pending = {4'b0001};
    }
    cp_vgein_switch_csrrw : cross priv_mode_hs, hstatus_csrrw, vgein_switch_rw;
    cp_vgein_switch_csrrs : cross priv_mode_hs, hstatus_csrrs, vgein_switch_set;
    cp_vgein_switch_csrrc : cross priv_mode_hs, hstatus_csrrc, vgein_switch_clear;

    // A single VS-level interrupt bit set or cleared in each CSR that holds a copy of it; the test then reads every copy
    csrs_csrc : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }
    // In VS-mode, sip and sie are vsip and vsie, which hold the VS-level bits one position lower
    alias_csr_vs : coverpoint ins.current.insn[31:20] {
        bins vsip = {CSR_SIP};
        bins vsie = {CSR_SIE};
    }
    vs_bit_vs : coverpoint ins.current.rs1_val {
        bins ssi = {2};
        bins sti = {32};
        bins sei = {512};
    }
    alias_csr_hs : coverpoint ins.current.insn[31:20] {
        bins hvip = {CSR_HVIP};
        bins hip  = {CSR_HIP};
        bins hie  = {CSR_HIE};
    }
    alias_csr_m : coverpoint ins.current.insn[31:20] {
        bins mip = {CSR_MIP};
        bins mie = {CSR_MIE};
    }
    vs_bit : coverpoint ins.current.rs1_val {
        bins vssi = {4};
        bins vsti = {64};
        bins vsei = {1024};
    }
    cp_vs_int_alias_vs : cross priv_mode_vs, csrs_csrc, alias_csr_vs, vs_bit_vs;
    cp_vs_int_alias_hs : cross priv_mode_hs, csrs_csrc, alias_csr_hs, vs_bit;
    cp_vs_int_alias_m  : cross priv_mode_m,  csrs_csrc, alias_csr_m,  vs_bit;
endgroup

function void interruptsh_sample(int hart, int issue, ins_t ins);
    InterruptsH_cg.sample(ins);
endfunction
