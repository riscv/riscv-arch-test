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

// Provide a fallback slice for VGEIN so the file compiles even if the platform
// has not defined one. Override with a platform definition when available.
`ifndef HSTATUS_VGEIN_SLICE
`define HSTATUS_VGEIN_SLICE 5:0
`endif

////////////////////////////////////////////////////////////////////////////////////////////////
// Machine mode coverpoints
////////////////////////////////////////////////////////////////////////////////////////////////

covergroup InterruptsH_M_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "coverage/RISCV_coverage_standard_coverpoints.svh"

    // building blocks
    mstatus_mie_one: coverpoint ins.current.csr[12'h300][3] {
        bins one = {1};
    }
    mstatus_mie_zero: coverpoint ins.current.csr[12'h300][3] {
        bins zero = {0};
    }
    csrr_mie: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b001100000100_00000_010_?????_1110011}; // csrrs rd, x0, mie
    }
    csrr_mip: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b001101000100_00000_010_?????_1110011}; // csrrs rd, x0, mip
    }
    hideleg_vsi_zero: coverpoint {ins.current.csr[12'h603][10],
                                  ins.current.csr[12'h603][6],
                                  ins.current.csr[12'h603][2]} {
        bins zero = {3'b000};
    }
    hideleg_vsi_ones: coverpoint {ins.current.csr[12'h603][10],
                                  ins.current.csr[12'h603][6],
                                  ins.current.csr[12'h603][2]} {
        bins ones = {3'b111};
    }
    hie_vsi_zero: coverpoint {ins.current.csr[12'h604][10],
                              ins.current.csr[12'h604][6],
                              ins.current.csr[12'h604][2]} {
        bins zero = {3'b000};
    }
    hie_vsi_ones: coverpoint {ins.current.csr[12'h604][10],
                              ins.current.csr[12'h604][6],
                              ins.current.csr[12'h604][2]} {
        bins ones = {3'b111};
    }
    hie_sgeie_one: coverpoint ins.current.csr[12'h604][12] {
        bins one = {1};
    }
    hvip_vsi_ones: coverpoint {ins.current.csr[12'h645][10],
                               ins.current.csr[12'h645][6],
                               ins.current.csr[12'h645][2]} {
        bins ones = {3'b111};
    }
    mie_vsi_ones: coverpoint {ins.current.csr[12'h304][10],
                              ins.current.csr[12'h304][6],
                              ins.current.csr[12'h304][2]} {
        bins ones = {3'b111};
    }
    mie_sgeie_zero: coverpoint ins.current.csr[12'h304][12] {
        bins zero = {0};
    }
    mie_sgeie_one: coverpoint ins.current.csr[12'h304][12] {
        bins one = {1};
    }
    mip_vsi_ones: coverpoint {ins.current.csr[12'h344][10],
                              ins.current.csr[12'h344][6],
                              ins.current.csr[12'h344][2]} {
        bins ones = {3'b111};
    }
    mip_sgeip_one: coverpoint ins.current.csr[12'h344][12] {
        bins one = {1};
    }
    hgeip_nonzero: coverpoint ins.current.csr[12'he12][15:0] {
        bins nonzero = default;
        bins zero    = {16'h0000};
    }
    mideleg_vsi_ro: coverpoint {ins.current.csr[12'h303][10],
                                ins.current.csr[12'h303][6],
                                ins.current.csr[12'h303][2]} {
        bins ro_one = {3'b111};
    }
    mideleg_sgei_ro: coverpoint ins.current.csr[12'h303][12] {
        bins one = {1};
    }

    // main coverpoints
    cp_mideleg:      cross priv_mode_m, mideleg_vsi_ro;
`ifdef GILEN_GT_0
    cp_mideleg_gei:  cross priv_mode_m, mideleg_sgei_ro;
`endif
    cp_mie:          cross priv_mode_m, csrr_mie, hie_vsi_ones, mie_vsi_ones;
    cp_mip:          cross priv_mode_m, csrr_mip, hvip_vsi_ones, mip_vsi_ones;
    cp_nohint_m:     cross priv_mode_m, mstatus_mie_one, hideleg_vsi_zero, mie_vsi_ones, mip_vsi_ones;
`ifdef GILEN_GT_0
    cp_mie_gilen:    cross priv_mode_m, csrr_mie, hie_vsi_ones, hie_sgeie_one, mie_sgeie_one;
    cp_mip_gilen:    cross priv_mode_m, csrr_mip, hgeip_nonzero, mip_sgeip_one;
`else
    cp_mie_gilen:    cross priv_mode_m, csrr_mie, hie_vsi_zero, hie_sgeie_one, mie_sgeie_zero;
`endif
endgroup

////////////////////////////////////////////////////////////////////////////////////////////////
// HS mode coverpoints
////////////////////////////////////////////////////////////////////////////////////////////////

covergroup InterruptsH_HS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "coverage/RISCV_coverage_standard_coverpoints.svh"

    // building blocks
    sstatus_sie: coverpoint ins.current.csr[12'h100][1] {
        bins zero = {0};
        bins one  = {1};
    }
    sstatus_sie_zero: coverpoint ins.current.csr[12'h100][1] {
        bins zero = {0};
    }
    sstatus_sie_one: coverpoint ins.current.csr[12'h100][1] {
        bins one = {1};
    }
    hideleg_vsi: coverpoint {ins.current.csr[12'h603][10],
                              ins.current.csr[12'h603][6],
                              ins.current.csr[12'h603][2]} {
        // autofill all 2^3 combinations
    }
    hideleg_vsi_zero: coverpoint {ins.current.csr[12'h603][10],
                                  ins.current.csr[12'h603][6],
                                  ins.current.csr[12'h603][2]} {
        bins zero = {3'b000};
    }
    hideleg_vsi_ones: coverpoint {ins.current.csr[12'h603][10],
                                  ins.current.csr[12'h603][6],
                                  ins.current.csr[12'h603][2]} {
        bins ones = {3'b111};
    }
    hideleg_vseie: coverpoint ins.current.csr[12'h603][10] {
        bins zero = {0};
        bins one  = {1};
    }
    hideleg_vstie: coverpoint ins.current.csr[12'h603][6] {
        bins zero = {0};
        bins one  = {1};
    }
    hideleg_vssie: coverpoint ins.current.csr[12'h603][2] {
        bins zero = {0};
        bins one  = {1};
    }
    hie_vsi: coverpoint {ins.current.csr[12'h604][10],
                         ins.current.csr[12'h604][6],
                         ins.current.csr[12'h604][2]} {
        // autofill all 2^3 combinations
    }
    hie_vsi_zero: coverpoint {ins.current.csr[12'h604][10],
                              ins.current.csr[12'h604][6],
                              ins.current.csr[12'h604][2]} {
        bins zero = {3'b000};
    }
    hie_vsi_ones: coverpoint {ins.current.csr[12'h604][10],
                              ins.current.csr[12'h604][6],
                              ins.current.csr[12'h604][2]} {
        bins ones = {3'b111};
    }
    hie_vseie: coverpoint ins.current.csr[12'h604][10] {
        bins zero = {0};
        bins one  = {1};
    }
    hie_vstie: coverpoint ins.current.csr[12'h604][6] {
        bins zero = {0};
        bins one  = {1};
    }
    hie_vssie: coverpoint ins.current.csr[12'h604][2] {
        bins zero = {0};
        bins one  = {1};
    }
    hie_sgeie_one: coverpoint ins.current.csr[12'h604][12] {
        bins one = {1};
    }
    hvip_vsi: coverpoint {ins.current.csr[12'h645][10],
                          ins.current.csr[12'h645][6],
                          ins.current.csr[12'h645][2]} {
        // autofill all 2^3 combinations
    }
    hvip_vsi_zero: coverpoint {ins.current.csr[12'h645][10],
                               ins.current.csr[12'h645][6],
                               ins.current.csr[12'h645][2]} {
        bins zero = {3'b000};
    }
    hvip_vsi_ones: coverpoint {ins.current.csr[12'h645][10],
                               ins.current.csr[12'h645][6],
                               ins.current.csr[12'h645][2]} {
        bins ones = {3'b111};
    }
    hvip_vseip: coverpoint ins.current.csr[12'h645][10] {
        bins zero = {0};
        bins one  = {1};
    }
    hvip_vstip: coverpoint ins.current.csr[12'h645][6] {
        bins zero = {0};
        bins one  = {1};
    }
    hvip_vssip: coverpoint ins.current.csr[12'h645][2] {
        bins zero = {0};
        bins one  = {1};
    }
    hip_vsi: coverpoint {ins.current.csr[12'h644][10],
                         ins.current.csr[12'h644][6],
                         ins.current.csr[12'h644][2]} {
        // autofill all 2^3 combinations
    }
    hip_vsi_ones: coverpoint {ins.current.csr[12'h644][10],
                              ins.current.csr[12'h644][6],
                              ins.current.csr[12'h644][2]} {
        bins ones = {3'b111};
    }
    hip_vseip: coverpoint ins.current.csr[12'h644][10] {
        bins zero = {0};
        bins one  = {1};
    }
    hip_vstip: coverpoint ins.current.csr[12'h644][6] {
        bins zero = {0};
        bins one  = {1};
    }
    hip_vssip: coverpoint ins.current.csr[12'h644][2] {
        bins zero = {0};
        bins one  = {1};
    }
    mie_vsi_ones: coverpoint {ins.current.csr[12'h304][10],
                              ins.current.csr[12'h304][6],
                              ins.current.csr[12'h304][2]} {
        bins ones = {3'b111};
    }
    mip_vsi_ones: coverpoint {ins.current.csr[12'h344][10],
                              ins.current.csr[12'h344][6],
                              ins.current.csr[12'h344][2]} {
        bins ones = {3'b111};
    }
    vsie_vsi: coverpoint {ins.current.csr[12'h204][10],
                          ins.current.csr[12'h204][6],
                          ins.current.csr[12'h204][2]} {
        // autofill all 2^3 combinations
    }
    vsie_vsi_ones: coverpoint {ins.current.csr[12'h204][10],
                               ins.current.csr[12'h204][6],
                               ins.current.csr[12'h204][2]} {
        bins ones = {3'b111};
    }
    vsip_vsi: coverpoint {ins.current.csr[12'h244][10],
                          ins.current.csr[12'h244][6],
                          ins.current.csr[12'h244][2]} {
        // autofill all 2^3 combinations
    }
    sie_ones: coverpoint {ins.current.csr[12'h104][9],
                          ins.current.csr[12'h104][5],
                          ins.current.csr[12'h104][1]} {
        bins ones = {3'b111};
    }
    sip_priority: coverpoint {ins.current.csr[12'h144][9],
                              ins.current.csr[12'h144][5],
                              ins.current.csr[12'h144][1]} {
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
    hgeie_nonzero: coverpoint ins.current.csr[12'h607][15:0] {
        bins nonzero = default;
        bins zero    = {16'h0000};
    }
    hgeie_all: coverpoint ins.current.csr[12'h607][15:0] {
        bins all_set = {16'hffff};
    }
    hgeip_nonzero: coverpoint ins.current.csr[12'he12][15:0] {
        bins nonzero = default;
        bins zero    = {16'h0000};
    }
    hgeip_all: coverpoint ins.current.csr[12'he12][15:0] {
        bins all_set = {16'hffff};
    }
    hstatus_vgein_zero: coverpoint ins.current.csr[12'h600][`HSTATUS_VGEIN_SLICE] {
        bins zero = {'0};
    }
    hstatus_vgein_nonzero: coverpoint ins.current.csr[12'h600][`HSTATUS_VGEIN_SLICE] {
        bins nonzero = default;
    }

    // main coverpoints
    cp_trigger_vsei:      cross priv_mode_s, sstatus_sie, hideleg_vseie, hie_vseie, hvip_vseip;
    cp_trigger_vsti:      cross priv_mode_s, sstatus_sie, hideleg_vstie, hie_vstie, hvip_vstip;
    cp_trigger_vssi:      cross priv_mode_s, sstatus_sie, hideleg_vssie, hie_vssie, hvip_vssip;
    cp_hip_write:         cross priv_mode_s, hip_vssip, hvip_vssip;
    cp_priority_en_vsi:   cross priv_mode_s, sstatus_sie_one, hideleg_vsi_zero, hie_vsi, hvip_vsi;
    cp_priority_deleg_vsi: cross priv_mode_s, sstatus_sie_one, hie_vsi_ones, hideleg_vsi, hvip_vsi;
    cp_priority_s:        cross priv_mode_s, sstatus_sie_one, hvip_vsi_ones, hideleg_vsi_zero, hie_vsi_ones, sie_ones, sip_priority;
    cp_hie:               cross priv_mode_s, csrr_hie, csrr_vsie, mie_vsi_ones, hideleg_vsi;
    cp_hip:               cross priv_mode_s, csrr_hip, csrr_vsip, mip_vsi_ones, hideleg_vsi;
    cp_hideleg:           cross priv_mode_s, hideleg_vsi_ones;
    cp_vsie:              cross priv_mode_s, csrr_vsie, hideleg_vsi, hie_vsi;
    cp_vsip:              cross priv_mode_s, csrr_vsip, hideleg_vsi, hip_vsi;
    cp_vsie_from_hie:     cross priv_mode_s, csrr_hie, hideleg_vsi, vsie_vsi_ones;

`ifdef GILEN_GT_0
    cp_hie_gilen:         cross priv_mode_s, csrr_hie, mie_vsi_ones, hie_sgeie_one;
    cp_priority_sgei:     cross priv_mode_s, sstatus_sie_one, hvip_vsi_ones, hideleg_vsi_zero, hie_sgeie_one, hgeip_nonzero, hgeie_nonzero;
    cp_priority_sgei_s:   cross priv_mode_s, sstatus_sie_one, hideleg_vsi_zero, hvip_vsi_ones, hie_sgeie_one, sie_ones, sip_priority, hgeip_nonzero, hgeie_nonzero;
    cp_trigger_sgei:      cross priv_mode_s, sstatus_sie, hgeip_nonzero, hgeie_nonzero, hie_sgeie_one;
    cp_hgeie:             cross priv_mode_s, sstatus_sie_zero, hgeip_nonzero, hgeie_nonzero;
    cp_trigger_vsei_hgeip: cross priv_mode_s, sstatus_sie_zero, hvip_vsi_zero, hideleg_vsi_zero, hie_vsi_zero, hgeip_nonzero, hgeie_nonzero, hstatus_vgein_nonzero;
    cp_hgeip0:            cross priv_mode_s, sstatus_sie_zero, hvip_vsi_zero, hideleg_vsi_zero, hie_vsi_zero, hgeip_all, hgeie_all, hstatus_vgein_zero;
`endif
endgroup

////////////////////////////////////////////////////////////////////////////////////////////////
// VS mode coverpoints
////////////////////////////////////////////////////////////////////////////////////////////////

covergroup InterruptsH_VS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "coverage/RISCV_coverage_standard_coverpoints.svh"

    priv_mode_vs: coverpoint ins.prev.mode {
        type_option.weight = 0;
        bins VS_mode = {2'b01};
    }
    vsstatus_sie: coverpoint ins.current.csr[12'h200][1] {
        bins zero = {0};
        bins one  = {1};
    }
    vsstatus_sie_one: coverpoint ins.current.csr[12'h200][1] {
        bins one = {1};
    }
    mstatus_mie_zero: coverpoint ins.current.csr[12'h300][3] {
        bins zero = {0};
    }
    hideleg_vsi: coverpoint {ins.current.csr[12'h603][10],
                              ins.current.csr[12'h603][6],
                              ins.current.csr[12'h603][2]} {
        // autofill all 2^3 combinations
    }
    hideleg_vsi_ones: coverpoint {ins.current.csr[12'h603][10],
                                  ins.current.csr[12'h603][6],
                                  ins.current.csr[12'h603][2]} {
        bins ones = {3'b111};
    }
    hie_vsi: coverpoint {ins.current.csr[12'h604][10],
                         ins.current.csr[12'h604][6],
                         ins.current.csr[12'h604][2]} {
        // autofill all 2^3 combinations
    }
    hie_vsi_ones: coverpoint {ins.current.csr[12'h604][10],
                              ins.current.csr[12'h604][6],
                              ins.current.csr[12'h604][2]} {
        bins ones = {3'b111};
    }
    hip_vsi: coverpoint {ins.current.csr[12'h644][10],
                         ins.current.csr[12'h644][6],
                         ins.current.csr[12'h644][2]} {
        // autofill all 2^3 combinations
    }
    hip_vsi_ones: coverpoint {ins.current.csr[12'h644][10],
                              ins.current.csr[12'h644][6],
                              ins.current.csr[12'h644][2]} {
        bins ones = {3'b111};
    }
    mie_ones: coverpoint ins.current.csr[12'h304][15:0] {
        wildcard bins ones = {16'b????1?1?1?1?1?1?};
    }
    mip_walking: coverpoint {ins.current.csr[12'h344][11],
                             ins.current.csr[12'h344][9],
                             ins.current.csr[12'h344][7],
                             ins.current.csr[12'h344][5],
                             ins.current.csr[12'h344][3],
                             ins.current.csr[12'h344][1]} {
        bins meip = {6'b100000};
        bins seip = {6'b010000};
        bins mtip = {6'b001000};
        bins stip = {6'b000100};
        bins msip = {6'b000010};
        bins ssip = {6'b000001};
    }
    mideleg_ones_zeros: coverpoint ins.current.csr[12'h303][15:0] {
        bins ones  = {16'b0000001000100010};
        bins zeros = {16'b0000000000000000};
    }
    mtinst_zero: coverpoint ins.current.csr[12'h34a][31:0] {
        bins zero = {32'h00000000};
    }
    htinst_zero: coverpoint ins.current.csr[12'h64a][31:0] {
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
    `include "coverage/RISCV_coverage_standard_coverpoints.svh"

    priv_mode_vu: coverpoint ins.prev.mode {
        type_option.weight = 0;
        bins VU_mode = {2'b00};
    }
    mstatus_mie_zero: coverpoint ins.current.csr[12'h300][3] {
        bins zero = {0};
    }
    hideleg_vsi: coverpoint {ins.current.csr[12'h603][10],
                              ins.current.csr[12'h603][6],
                              ins.current.csr[12'h603][2]} {
        // autofill all 2^3 combinations
    }
    hideleg_vsi_ones: coverpoint {ins.current.csr[12'h603][10],
                                  ins.current.csr[12'h603][6],
                                  ins.current.csr[12'h603][2]} {
        bins ones = {3'b111};
    }
    hie_vsi: coverpoint {ins.current.csr[12'h604][10],
                         ins.current.csr[12'h604][6],
                         ins.current.csr[12'h604][2]} {
        // autofill all 2^3 combinations
    }
    hie_vsi_ones: coverpoint {ins.current.csr[12'h604][10],
                              ins.current.csr[12'h604][6],
                              ins.current.csr[12'h604][2]} {
        bins ones = {3'b111};
    }
    hip_vsi: coverpoint {ins.current.csr[12'h644][10],
                         ins.current.csr[12'h644][6],
                         ins.current.csr[12'h644][2]} {
        // autofill all 2^3 combinations
    }
    hip_vsi_ones: coverpoint {ins.current.csr[12'h644][10],
                              ins.current.csr[12'h644][6],
                              ins.current.csr[12'h644][2]} {
        bins ones = {3'b111};
    }
    mie_ones: coverpoint ins.current.csr[12'h304][15:0] {
        wildcard bins ones = {16'b????1?1?1?1?1?1?};
    }
    mip_walking: coverpoint {ins.current.csr[12'h344][11],
                             ins.current.csr[12'h344][9],
                             ins.current.csr[12'h344][7],
                             ins.current.csr[12'h344][5],
                             ins.current.csr[12'h344][3],
                             ins.current.csr[12'h344][1]} {
        bins meip = {6'b100000};
        bins seip = {6'b010000};
        bins mtip = {6'b001000};
        bins stip = {6'b000100};
        bins msip = {6'b000010};
        bins ssip = {6'b000001};
    }
    mideleg_ones_zeros: coverpoint ins.current.csr[12'h303][15:0] {
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
    `include "coverage/RISCV_coverage_standard_coverpoints.svh"

    hideleg_vsi_ones: coverpoint {ins.current.csr[12'h603][10],
                                  ins.current.csr[12'h603][6],
                                  ins.current.csr[12'h603][2]} {
        bins ones = {3'b111};
    }
    hie_vsi_ones: coverpoint {ins.current.csr[12'h604][10],
                              ins.current.csr[12'h604][6],
                              ins.current.csr[12'h604][2]} {
        bins ones = {3'b111};
    }
    hip_vsi_ones: coverpoint {ins.current.csr[12'h644][10],
                              ins.current.csr[12'h644][6],
                              ins.current.csr[12'h644][2]} {
        bins ones = {3'b111};
    }

    // main coverpoints
    cp_vsint_disabled_u: cross priv_mode_u, hideleg_vsi_ones, hip_vsi_ones, hie_vsi_ones;
endgroup

function void interruptsh_sample(int hart, int issue, ins_t ins);
    InterruptsH_M_cg.sample(ins);
    InterruptsH_HS_cg.sample(ins);
    InterruptsH_VS_cg.sample(ins);
    InterruptsH_VU_cg.sample(ins);
    InterruptsH_U_cg.sample(ins);
endfunction
