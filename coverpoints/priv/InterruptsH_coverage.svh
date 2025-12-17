///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Neil Chulani nchulani@g.hmc.edu 30 Oct 2025
//
// Copyright (C) 2025 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSH

////////////////////////////////////////////////////////////////////////////////////////////////
// Machine mode coverpoints
////////////////////////////////////////////////////////////////////////////////////////////////

covergroup InterruptsH_M_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks
    mstatus_mie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie") {
        bins one = {1};
    }
    mstatus_mie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie") {
        bins zero = {0};
    }
    csrr_any: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b????????????_00000_010_?????_1110011};
    }
    csr_read_addr: coverpoint ins.current.insn[31:20] {
        bins mie = {12'h304};
        bins mip = {12'h344};
        bins hie = {12'h604};
        bins hip = {12'h644};
    }
    hideleg_vsi_zero: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        bins zero = {3'b000};
    }
    hideleg_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        bins ones = {3'b111};
    }
    hie_vsi_zero: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        bins zero = {3'b000};
    }
    hie_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        bins ones = {3'b111};
    }
    hie_sgeie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "sgeie") {
        bins one = {1};
    }
    hvip_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vseip")),
                               1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vstip")),
                               1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vssip"))} {
        bins ones = {3'b111};
    }
    mie_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "vgeie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "vssie"))} {
        bins ones = {3'b111};
    }
    mie_sgeie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "sgeie") {
        bins zero = {0};
    }
    mie_sgeie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "sgeie") {
        bins one = {1};
    }
    mip_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "vgeip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "vssip"))} {
        bins ones = {3'b111};
    }
    mip_sgeip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "sgeip") {
        bins one = {1};
    }
    hgeip_nonzero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "pending")[15:0] {
        bins nonzero = default;
    }
    mideleg_vsi_ro: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "vgeip")),
                                1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "vstip")),
                                1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "vssip"))} {
        bins ro_one = {3'b111};
    }
    mideleg_sgei_ro: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "sgeip") {
        bins one = {1};
    }

    // main coverpoints
    cp_mideleg:      cross priv_mode_m, mideleg_vsi_ro;
    cp_mie:          cross priv_mode_m, csrr_any, csr_read_addr, hie_vsi_ones, mie_vsi_ones;
    cp_mip:          cross priv_mode_m, csrr_any, csr_read_addr, hvip_vsi_ones, mip_vsi_ones;
    cp_nohint_m:     cross priv_mode_m, mstatus_mie_one, hideleg_vsi_zero, mie_vsi_ones, mip_vsi_ones;
`ifdef GILEN_GT_0
    cp_mie_gilen:    cross priv_mode_m, csrr_any, csr_read_addr, hie_vsi_ones, hie_sgeie_one, mie_sgeie_one;
    cp_mip_gilen:    cross priv_mode_m, csrr_any, csr_read_addr, hgeip_nonzero, mip_sgeip_one;
`else
    cp_mie_gilen:    cross priv_mode_m, csrr_any, csr_read_addr, hie_vsi_zero, hie_sgeie_one, mie_sgeie_zero;
`endif
endgroup

////////////////////////////////////////////////////////////////////////////////////////////////
// HS mode coverpoints
////////////////////////////////////////////////////////////////////////////////////////////////

covergroup InterruptsH_HS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks
    sstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie") {
        bins zero = {0};
        bins one  = {1};
    }
    sstatus_sie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie") {
        bins zero = {0};
    }
    sstatus_sie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie") {
        bins one = {1};
    }
    hideleg_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        // autofill all 2^3 combinations
    }
    hideleg_vsi_zero: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        bins zero = {3'b000};
    }
    hideleg_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        bins ones = {3'b111};
    }
    hideleg_vseie: coverpoint 1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")) {
        bins zero = {0};
        bins one  = {1};
    }
    hideleg_vstie: coverpoint 1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")) {
        bins zero = {0};
        bins one  = {1};
    }
    hideleg_vssie: coverpoint 1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip")) {
        bins zero = {0};
        bins one  = {1};
    }
    hie_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        // autofill all 2^3 combinations
    }
    hie_vsi_zero: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        bins zero = {3'b000};
    }
    hie_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        bins ones = {3'b111};
    }
    hie_vseie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie") {
        bins zero = {0};
        bins one  = {1};
    }
    hie_vstie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie") {
        bins zero = {0};
        bins one  = {1};
    }
    hie_vssie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie") {
        bins zero = {0};
        bins one  = {1};
    }
    hie_sgeie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "sgeie") {
        bins one = {1};
    }
    hvip_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vseip")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vstip")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vssip"))} {
        // autofill all 2^3 combinations
    }
    hvip_vsi_zero: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vseip")),
                               1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vstip")),
                               1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vssip"))} {
        bins zero = {3'b000};
    }
    hvip_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vseip")),
                               1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vstip")),
                               1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vssip"))} {
        bins ones = {3'b111};
    }
    hvip_vseip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vseip") {
        bins one  = {1};
    }
    hvip_vstip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vstip") {
        bins one  = {1};
    }
    hvip_vssip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vssip") {
        bins one  = {1};
    }
    hip_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vseip")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vstip")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vssip"))} {
        // autofill all 2^3 combinations
    }
    hip_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vseip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vssip"))} {
        bins ones = {3'b111};
    }
    hip_vseip: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vseip") {
        bins zero = {0};
        bins one  = {1};
    }
    hip_vstip: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vstip") {
        bins zero = {0};
        bins one  = {1};
    }
    hip_vssip: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vssip") {
        bins zero = {0};
        bins one  = {1};
    }
    mie_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "vgeie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "vssie"))} {
        bins ones = {3'b111};
    }
    mip_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "vgeip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "vssip"))} {
        bins ones = {3'b111};
    }
    vsie_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsie", "seie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsie", "stie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsie", "ssie"))} {
        // autofill all 2^3 combinations
    }
    vsie_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsie", "seie")),
                               1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsie", "stie")),
                               1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsie", "ssie"))} {
        bins ones = {3'b111};
    }
    vsip_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsip", "seip")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsip", "stip")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsip", "ssip"))} {
        // autofill all 2^3 combinations
    }
    sie_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "seie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "stie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sie", "ssie"))} {
        bins ones = {3'b111};
    }
    sip_priority: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "seip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "stip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sip", "ssip"))} {
        bins none = {3'b000};
        bins ssip = {3'b001};
        bins stip = {3'b010};
        bins seip = {3'b100};
    }
    csrr_hie: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b011000000100_00000_010_?????_1110011};
    }
    csrr_hip: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b011001000100_00000_010_?????_1110011};
    }
    csrr_vsie: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b001000000100_00000_010_?????_1110011};
    }
    csrr_vsip: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b001001000100_00000_010_?????_1110011};
    }
    hgeie_nonzero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "enable")[15:0] {
        bins nonzero = default;
    }
    hgeie_all: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "enable")[15:0] {
        bins all_set = {16'hffff};
    }
    hgeie_onehot: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeie", "enable")[15:0] {
        bins single_bit[] = {16'h0001,16'h0002,16'h0004,16'h0008,
                             16'h0010,16'h0020,16'h0040,16'h0080,
                             16'h0100,16'h0200,16'h0400,16'h0800,
                             16'h1000,16'h2000,16'h4000,16'h8000};
    }
    hgeip_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "pending")[15:0] {
        bins zero = {16'h0000};
    }
    hgeip_nonzero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "pending")[15:0] {
        bins nonzero = default;
    }
    hgeip_onehot: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "pending")[15:0] {
        bins single_bit[] = {16'h0001,16'h0002,16'h0004,16'h0008,
                             16'h0010,16'h0020,16'h0040,16'h0080,
                             16'h0100,16'h0200,16'h0400,16'h0800,
                             16'h1000,16'h2000,16'h4000,16'h8000};
    }
    hgeip_all: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgeip", "pending")[15:0] {
        bins all_set = {16'hffff};
    }
    hstatus_vgein_zero: coverpoint ins.prev.csr[12'h600][`HSTATUS_VGEIN_SLICE] {
        bins zero = {'0};
    }
    hstatus_vgein_nonzero: coverpoint ins.prev.csr[12'h600][`HSTATUS_VGEIN_SLICE] {
        bins nonzero = {[6'd1:6'd63]};
    }

    // main coverpoints
    cp_trigger_vsei:      cross priv_mode_hs, sstatus_sie, hideleg_vseie, hie_vseie, hvip_vseip_one;
    cp_trigger_vsti:      cross priv_mode_hs, sstatus_sie, hideleg_vstie, hie_vstie, hvip_vstip_one;
    cp_trigger_vssi:      cross priv_mode_hs, sstatus_sie, hideleg_vssie, hie_vssie, hvip_vssip_one;
    cp_hip_write:         cross priv_mode_hs, hip_vssip, hvip_vssip_one;
    cp_priority_en_vsi:   cross priv_mode_hs, sstatus_sie_one, hideleg_vsi_zero, hie_vsi, hvip_vsi;
    cp_priority_deleg_vsi: cross priv_mode_hs, sstatus_sie_one, hie_vsi_ones, hideleg_vsi, hvip_vsi;
    cp_priority_s:        cross priv_mode_hs, sstatus_sie_one, hvip_vsi_ones, hideleg_vsi_zero, hie_vsi_ones, sie_ones, sip_priority;
    cp_hie:               cross priv_mode_hs, csrr_hie, csrr_vsie, mie_vsi_ones, hideleg_vsi;
    cp_hip:               cross priv_mode_hs, csrr_hip, csrr_vsip, mip_vsi_ones, hideleg_vsi;
    cp_hideleg:           cross priv_mode_hs, hideleg_vsi_ones;
    cp_vsie:              cross priv_mode_hs, csrr_vsie, hideleg_vsi, hie_vsi;
    cp_vsip:              cross priv_mode_hs, csrr_vsip, hideleg_vsi, hip_vsi;
    cp_vsie_from_hie:     cross priv_mode_hs, csrr_hie, hideleg_vsi, vsie_vsi_ones;

`ifdef GILEN_GT_0
    cp_hie_gilen:         cross priv_mode_hs, csrr_any, csr_read_addr, mie_vsi_ones, mie_sgeie_one, hie_sgeie_one;
    cp_priority_sgei:     cross priv_mode_hs, sstatus_sie_one, hvip_vsi_ones, hideleg_vsi_zero, hie_sgeie_one, hgeip_nonzero, hgeie_nonzero;
    cp_priority_sgei_s:   cross priv_mode_hs, sstatus_sie_one, hideleg_vsi_zero, hvip_vsi_ones, hie_sgeie_one, sie_ones, sip_priority, hgeip_nonzero, hgeie_nonzero;
    cp_trigger_sgei:      cross priv_mode_hs, sstatus_sie, hgeip_nonzero, hgeie_nonzero, hie_sgeie_one;
    cp_hgeie:             cross priv_mode_hs, sstatus_sie_zero, hgeip_zero, hgeip_onehot, hgeip_all, hgeie_onehot;
    cp_trigger_vsei_hgeip: cross priv_mode_hs, sstatus_sie_zero, hvip_vsi_zero, hideleg_vsi_zero, hie_vsi_zero, hgeip_nonzero, hgeie_nonzero, hstatus_vgein_nonzero;
    cp_hgeip0:            cross priv_mode_hs, sstatus_sie_zero, hvip_vsi_zero, hideleg_vsi_zero, hie_vsi_zero, hgeip_all, hgeie_all, hstatus_vgein_zero;
`endif
endgroup

////////////////////////////////////////////////////////////////////////////////////////////////
// VS mode coverpoints
////////////////////////////////////////////////////////////////////////////////////////////////

covergroup InterruptsH_VS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks
    vsstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sie") {
        bins zero = {0};
        bins one  = {1};
    }
    vsstatus_sie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sie") {
        bins one = {1};
    }
    mstatus_mie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie") {
        bins zero = {0};
    }
    hideleg_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        // autofill all 2^3 combinations
    }
    hideleg_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        bins ones = {3'b111};
    }
    hie_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        // autofill all 2^3 combinations
    }
    hie_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        bins ones = {3'b111};
    }
    hip_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vseip")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vstip")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vssip"))} {
        // autofill all 2^3 combinations
    }
    hip_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vseip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vssip"))} {
        bins ones = {3'b111};
    }
    mie_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "meie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "seie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mtie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "stie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "msee")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "ssie"))} {
        bins ones = {6'b111111};
    }
    mip_walking: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "meip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "seip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mtip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "stip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "msip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "ssip"))} {
        bins meip = {6'b100000};
        bins seip = {6'b010000};
        bins mtip = {6'b001000};
        bins stip = {6'b000100};
        bins msip = {6'b000010};
        bins ssip = {6'b000001};
    }
    mideleg_ones_zeros: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, 12'h303, "mideleg_raw", "")[15:0] {
        bins ones  = {16'b0000001000100010};
        bins zeros = {16'b0000000000000000};
    }
    mtinst_zero: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, 12'h34a, "mtinst", "")[31:0] {
        bins zero = {32'h00000000};
    }
    htinst_zero: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, 12'h64a, "htinst", "")[31:0] {
        bins zero = {32'h00000000};
    }

    // main coverpoints
    cp_hideleg_hip_vs: cross priv_mode_vs, hideleg_vsi, hip_vsi, hie_vsi_ones, vsstatus_sie_one;
    cp_hideleg_hie_vs: cross priv_mode_vs, hideleg_vsi, hie_vsi, hip_vsi_ones, vsstatus_sie_one;
    cp_hip_hie_vs:     cross priv_mode_vs, hip_vsi, hie_vsi, hideleg_vsi_ones, vsstatus_sie_one;
    cp_sie_vs:         cross priv_mode_vs, hideleg_vsi_ones, hip_vsi_ones, hie_vsi_ones, vsstatus_sie;
    cp_mideleg_mip_vs: cross priv_mode_vs, mstatus_mie_zero, mideleg_ones_zeros, mip_walking, mie_ones, vsstatus_sie_one;
    cp_mtinst:         cross priv_mode_vs, mtinst_zero;
    cp_htinst:         cross priv_mode_vs, htinst_zero;
endgroup

////////////////////////////////////////////////////////////////////////////////////////////////
// VU mode coverpoints
////////////////////////////////////////////////////////////////////////////////////////////////

covergroup InterruptsH_VU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks
    mstatus_mie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie") {
        bins zero = {0};
    }
    hideleg_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        // autofill all 2^3 combinations
    }
    hideleg_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        bins ones = {3'b111};
    }
    hie_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        // autofill all 2^3 combinations
    }
    hie_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        bins ones = {3'b111};
    }
    hip_vsi: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vseip")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vstip")),
                         1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vssip"))} {
        // autofill all 2^3 combinations
    }
    hip_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vseip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vssip"))} {
        bins ones = {3'b111};
    }
    mie_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "meie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "seie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mtie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "stie")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "msee")),
                          1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "ssie"))} {
        bins ones = {6'b111111};
    }
    mip_walking: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "meip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "seip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "mtip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "stip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "msip")),
                             1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "ssip"))} {
        bins meip = {6'b100000};
        bins seip = {6'b010000};
        bins mtip = {6'b001000};
        bins stip = {6'b000100};
        bins msip = {6'b000010};
        bins ssip = {6'b000001};
    }
    mideleg_ones_zeros: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, 12'h303, "mideleg_raw", "")[15:0] {
        bins ones  = {16'b0000001000100010};
        bins zeros = {16'b0000000000000000};
    }

    // main coverpoints
    cp_hideleg_hip_vu: cross priv_mode_vu, hideleg_vsi, hip_vsi, hie_vsi_ones;
    cp_hideleg_hie_vu: cross priv_mode_vu, hideleg_vsi, hie_vsi, hip_vsi_ones;
    cp_hip_hie_vu:     cross priv_mode_vu, hip_vsi, hie_vsi, hideleg_vsi_ones;
    cp_mideleg_mip_vu: cross priv_mode_vu, mstatus_mie_zero, mideleg_ones_zeros, mip_walking, mie_ones;
endgroup

////////////////////////////////////////////////////////////////////////////////////////////////
// U mode coverpoints
////////////////////////////////////////////////////////////////////////////////////////////////

covergroup InterruptsH_U_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    priv_mode_u_novirt: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
        type_option.weight = 0;
        bins U_mode = {3'b000};
    }
    hideleg_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vgeip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vstip")),
                                  1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip"))} {
        bins ones = {3'b111};
    }
    hie_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vseie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vstie")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie"))} {
        bins ones = {3'b111};
    }
    hip_vsi_ones: coverpoint {1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vseip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vstip")),
                              1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hip", "vssip"))} {
        bins ones = {3'b111};
    }

    // main coverpoints
    cp_vsint_disabled_u: cross priv_mode_u_novirt, hideleg_vsi_ones, hip_vsi_ones, hie_vsi_ones;
endgroup

function void interruptsh_sample(int hart, int issue, ins_t ins);
    InterruptsH_M_cg.sample(ins);
    InterruptsH_HS_cg.sample(ins);
    InterruptsH_VS_cg.sample(ins);
    InterruptsH_VU_cg.sample(ins);
    InterruptsH_U_cg.sample(ins);
endfunction
