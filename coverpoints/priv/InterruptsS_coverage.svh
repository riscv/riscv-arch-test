///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 18 Feb 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSS

covergroup InterruptsS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    mstatus_mie: coverpoint ins.current.csr[12'h300][3]  {
        // autofill 0/1
    }
    mstatus_mie_zero: coverpoint ins.current.csr[12'h300][3] {
        bins zero = {0};
    }
    mstatus_mie_one: coverpoint ins.current.csr[12'h300][3] {
        bins one = {1};
    }
    mstatus_mie_rise: coverpoint ins.current.csr[12'h300][3] {
        bins rise = (0 => 1);
    }
    mstatus_sie: coverpoint ins.current.csr[12'h300][1] {
        // autofill 0/1
    }
    mstatus_sie_one: coverpoint ins.current.csr[12'h300][1] {
        bins one = {1};
    }
    prev_mstatus_sie_zero: coverpoint ins.prev.csr[12'h300][1] {
        bins zero = {0};
    }
    prev_mstatus_sie_one: coverpoint ins.prev.csr[12'h300][1] {
        bins one = {1};
    }
    mstatus_tw:  coverpoint ins.current.csr[12'h300][21] {
        // autofill 0/1
    }
    mstatus_tw_one:  coverpoint ins.current.csr[12'h300][21] {
        bins one = {1};
    }
    mideleg_msi_zero: coverpoint ins.current.csr[12'h303][3] {
        bins zero = {0};
    }
    mideleg_mti_zero: coverpoint ins.current.csr[12'h303][7] {
        bins zero = {0};
    }
    mideleg_sei: coverpoint ins.current.csr[12'h303][9] {
        // autofill 0/1
    }
    mideleg_ssi: coverpoint ins.current.csr[12'h303][1] {
        // autofill 0/1
    }
    mideleg_mei_zero: coverpoint ins.current.csr[12'h303][11] {
        bins zero = {0};
    }
    mideleg_zeros: coverpoint ins.current.csr[12'h303][15:0] {
        bins zeros = {16'b0000000000000000}; // zeros in every field that is not tied to zero
    }
    mideleg_ones: coverpoint ins.current.csr[12'h303][15:0] {
        bins ones  = {16'b0000001000100010}; //  ones in every field that is not tied to zero (only supervisor delegable)
    }
    mideleg_ones_zeros: coverpoint ins.current.csr[12'h303][15:0] {
        bins ones  = {16'b0000001000100010}; //  ones in every field that is not tied to zero (only supervisor delegable)
        bins zeros = {16'b0000000000000000}; // zeros in every field that is not tied to zero
    }
    mie_msie: coverpoint ins.current.csr[12'h304][3] {
        // autofill 0/1
    }
    mie_mtie: coverpoint ins.current.csr[12'h304][7] {
        // autofill 0/1
    }
    mie_seie: coverpoint ins.current.csr[12'h304][9] {
        // autofill 0/1
    }
    mie_meie: coverpoint ins.current.csr[12'h304][11] {
        // autofill 0/1
    }
    mie_mtie_one: coverpoint ins.current.csr[12'h304][7] {
        bins one = {1};
    }
    mie_ones: coverpoint ins.current.csr[12'h304][15:0] {
        wildcard bins ones = {16'b????1?1?1?1?1?1?}; // ones in every field that is not tied to zero
    }
    mip_msip: coverpoint ins.current.csr[12'h344][3] {
        // autofill 0/1
    }
    mip_mtip: coverpoint ins.current.csr[12'h344][7] {
        // autofill 0/1
    }
    mip_seip: coverpoint ins.current.csr[12'h344][9] {
        // autofill 0/1
    }
    mip_meip: coverpoint ins.current.csr[12'h344][11] {
        // autofill 0/1
    }
    mip_ssip_one: coverpoint ins.current.csr[12'h344][1] {
        bins one = {1};
    }
    mip_msip_one: coverpoint ins.current.csr[12'h344][3] {
        bins one = {1};
    }
    mip_stip_one: coverpoint ins.current.csr[12'h344][5] {
        bins one = {1};
    }
    mip_mtip_one: coverpoint ins.current.csr[12'h344][7] {
        bins one = {1};
    }
    // mip_seip_zero: coverpoint ins.current.csr[12'h344][9] {
    //     bins zero = {0};
    // }
    mip_seip_one: coverpoint ins.current.csr[12'h344][9] {
        bins one = {1};
    }
    prev_mip_seip_one: coverpoint ins.prev.csr[12'h344][9] {
        bins one = {1};
    }
    mip_seip_rise: coverpoint ins.current.csr[12'h344][9] {
        bins rise = (0 => 1);
    }
    mip_meip_one: coverpoint ins.current.csr[12'h344][11] {
        bins one = {1};
    }
    mip_ones: coverpoint ins.current.csr[12'h344][15:0] {
        wildcard bins ones = {16'b0000101010101010}; // ones in every field that is not tied to zero
    }
    mip_ones_s: coverpoint ins.current.csr[12'h344][15:0] {
        wildcard bins ones = {16'b0000001000100010}; // ones in every supervisor field that is not tied to zero
    }
    mie_walking: coverpoint {ins.current.csr[12'h304][11],
                             ins.current.csr[12'h304][9],
                             ins.current.csr[12'h304][7],
                             ins.current.csr[12'h304][5],
                             ins.current.csr[12'h304][3],
                             ins.current.csr[12'h304][1]} {
        bins meie = {6'b100000};
        bins seie = {6'b010000};
        bins mtie = {6'b001000};
        bins stie = {6'b000100};
        bins msie = {6'b000010};
        bins ssie = {6'b000001};
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
    mie_s_ones: coverpoint {ins.current.csr[12'h304][9],
                            ins.current.csr[12'h304][5],
                            ins.current.csr[12'h304][1]} {
        bins ones = {3'b111};
    }
    mip_s_walking: coverpoint {ins.current.csr[12'h344][9],
                               ins.current.csr[12'h344][5],
                               ins.current.csr[12'h344][1]}  {
        bins seip = {3'b100};
        bins stip = {3'b010};
        bins ssip = {3'b001};
    }
    mie_m_walking: coverpoint {ins.current.csr[12'h304][11],
                               ins.current.csr[12'h304][7],
                               ins.current.csr[12'h304][3]} {
        bins meie = {3'b100};
        bins mtie = {3'b010};
        bins msie = {3'b001};
    }
    mip_m_walking: coverpoint {ins.current.csr[12'h344][11],
                               ins.current.csr[12'h344][7],
                               ins.current.csr[12'h344][3]} {
        bins meip = {3'b100};
        bins mtip = {3'b010};
        bins msip = {3'b001};
    }
    mie_combinations: coverpoint {ins.current.csr[12'h304][11],
                                  ins.current.csr[12'h304][9],
                                  ins.current.csr[12'h304][7],
                                  ins.current.csr[12'h304][5],
                                  ins.current.csr[12'h304][3],
                                  ins.current.csr[12'h304][1]} {
        // auto fills all 2^6 combinations
    }
    mip_combinations: coverpoint {ins.current.csr[12'h344][11],
                                  ins.current.csr[12'h344][9],
                                  ins.current.csr[12'h344][7],
                                  ins.current.csr[12'h344][5],
                                  ins.current.csr[12'h344][3],
                                  ins.current.csr[12'h344][1]} {
        // auto fills all 2^6 combinations
    }
    mideleg_combinations: coverpoint {ins.current.csr[12'h303][9],
                                      ins.current.csr[12'h303][5],
                                      ins.current.csr[12'h303][1]} {
        // auto fills all 2^3 combinations (assuming only supervisor interrupts are delegable)
    }
    mip_mie_eq: coverpoint (ins.current.csr[12'h304][11:0] == ins.current.csr[12'h344][11:0]) {
        bins equal = {1};
    }
    mideleg_mie_eq: coverpoint (ins.current.csr[12'h303][11:0] == ins.current.csr[12'h344][11:0]) {
        bins equal = {1};
    }
    stvec_mode: coverpoint ins.current.csr[12'h105][1:0] {
        bins direct   = {2'b00};
        bins vector   = {2'b01};
    }
    stvec_vectored: coverpoint ins.current.csr[12'h105][1:0] {
        bins vector   = {2'b01};
    }
    mtvec_direct: coverpoint ins.current.csr[12'h305][1:0] {
        bins direct   = {2'b00};
    }
    mtvec_vectored: coverpoint ins.current.csr[12'h305][1:0] {
        bins vector   = {2'b01};
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b????????????_?????_001_?????_1110011};
    }
    csrrs: coverpoint ins.current.insn {
        wildcard bins csrrs = {32'b????????????_?????_010_?????_1110011};
    }
    csrrc: coverpoint ins.current.insn {
        wildcard bins csrrc = {32'b????????????_?????_011_?????_1110011};
    }
    write_mip_seip: coverpoint ins.current.rs1_val[9] iff (ins.current.insn[31:20] == 12'h344) {
        bins write_seip = {1};
    }
    write_sip_ssip: coverpoint ins.current.rs1_val[1] iff (ins.current.insn[31:20] == 12'h144) {
        bins write_ssip = {1};
    }
    write_sstatus_sie: coverpoint ins.current.rs1_val[1] iff ( ins.current.insn[31:20] == 12'h100) {
        bins write_sie = {1};
    }
    write_mstatus_mie: coverpoint ins.current.rs1_val[3] iff ( ins.current.insn[31:20] == 12'h300) {
        bins write_mie = {1};
    }
    wfi: coverpoint ins.current.insn {
        bins wfi = {32'b0001000_00101_00000_000_00000_1110011};
    }
    timeout: coverpoint ins.current.csr[12'h344][7] iff (ins.trap == 1) {
        bins no_timer_int = {0};
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
    s_ext_intr: coverpoint ins.current.s_ext_intr {
        // autofill 0/1
    }
    s_ext_intr_high: coverpoint ins.current.s_ext_intr {
        bins sei = {1};
    }
    s_ext_intr_low: coverpoint ins.current.s_ext_intr {
        bins no_sei = {0};
    }

    // main coverpoints
    cp_trigger_mti:             cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones_zeros, mip_mtip_one;
    cp_trigger_msi:             cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones_zeros, mip_msip_one;
    cp_trigger_mei:             cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones_zeros, mip_meip_one;
    cp_trigger_sti:             cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones_zeros, mip_stip_one;
    cp_trigger_ssi_mip:         cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones_zeros, mip_ssip_one;
    cp_trigger_ssi_sip:         cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones_zeros, csrrs, write_sip_ssip;
    cp_trigger_sei:             cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones_zeros, mip_seip_one, s_ext_intr_high;
    cp_trigger_sei_seip:        cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones_zeros, mip_seip_one, s_ext_intr_low;
    cp_trigger_changingtos_sti: cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_zero, mie_ones, mideleg_ones, mip_stip_one, csrrs, write_sstatus_sie;
    cp_trigger_changingtos_ssi: cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_zero, mie_ones, mideleg_ones, mip_ssip_one, csrrs, write_sstatus_sie;
    cp_trigger_changingtos_sei: cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_zero, mie_ones, mideleg_ones, mip_seip_one, csrrs, write_sstatus_sie;
    cp_interrupts_s:            cross priv_mode_s, mstatus_mie_zero, mideleg_ones_zeros, mtvec_direct, mip_walking, mie_walking;
    cp_vectored_s:              cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_ones, mideleg_ones, stvec_mode, mip_walking;
    cp_priority_mip_s:          cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mip_combinations, mie_ones,   mideleg_ones_zeros;
    cp_priority_mie_s:          cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_combinations, mip_ones,   mideleg_ones_zeros;
    cp_priority_both_s:         cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_combinations, mip_mie_eq, mideleg_ones_zeros;
    cp_priority_mideleg_m:      cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mideleg_combinations, mip_ones_s, mie_ones;
    cp_priority_mideleg_s:      cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mideleg_combinations, mip_ones_s, mideleg_mie_eq;
    cp_wfi_s:                   cross priv_mode_s, wfi, mstatus_mie, mstatus_sie, mideleg_ones_zeros, mstatus_tw, mie_mtie_one, mip_mtip_one; // could cause funky coverage since WFI often doesn't retire. Revisit later
    cp_wfi_timeout_s:           cross priv_mode_s, wfi, mstatus_mie, mstatus_sie, mideleg_ones_zeros, mstatus_tw_one, mie_mtie, timeout;

    cp_interrupts_m:            cross priv_mode_m, mstatus_mie, mtvec_direct, mideleg_ones_zeros, mip_walking, mie_walking;
    cp_vectored_m:              cross priv_mode_m, mstatus_mie_one, mtvec_vectored, mideleg_zeros, mip_s_walking, mie_s_ones;
    cp_priority_mip_m:          cross priv_mode_m, mie_ones, mideleg_zeros, mip_combinations, mstatus_mie_rise;
    cp_priority_mie_m:          cross priv_mode_m, mip_ones, mideleg_zeros, mie_combinations, mstatus_mie_rise;
    cp_wfi_m:                   cross priv_mode_m, wfi, mstatus_mie, mstatus_sie, mideleg_ones, mstatus_tw, mie_mtie_one, mip_mtip_one;
    cp_trigger_mti_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_mtip_one, csrrs, write_mstatus_mie;
    cp_trigger_ssi_sip_m:       cross priv_mode_m, mstatus_mie, mie_ones, mideleg_ssi, csrrs, write_sip_ssip;
    cp_trigger_msi_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_msip_one, csrrs, write_mstatus_mie;
    cp_trigger_mei_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_meip_one, csrrs, write_mstatus_mie;
    cp_trigger_sti_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_stip_one, csrrs, write_mstatus_mie;
    cp_trigger_ssi_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_ssip_one, csrrs, write_mstatus_mie;
    cp_trigger_sei_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_seip_one, csrrs, write_mstatus_mie;
    cp_sei1:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, s_ext_intr_low, csrrw, write_mip_seip;
    cp_sei2:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, s_ext_intr_low, csrrs, write_mip_seip;
    cp_sei3:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, s_ext_intr_high;
    cp_sei4:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, prev_mip_seip_one, s_ext_intr_low,  csrrc, write_mip_seip;
    cp_sei5:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, prev_mip_seip_one, s_ext_intr_high, csrrc, write_mip_seip;
    cp_sei6_7:                  cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, s_ext_intr, mip_seip;
    cp_global_ie:               cross priv_mode_m, mstatus_mie, mstatus_sie, mip_m_walking, mip_mie_eq;

    cp_user_mti:                cross priv_mode_u, mstatus_mie, mstatus_sie, stvec_mode, mideleg_mti_zero, mie_mtie, mip_mtip;
    cp_user_msi:                cross priv_mode_u, mstatus_mie, mstatus_sie, stvec_mode, mideleg_msi_zero, mie_msie, mip_msip;
    cp_user_mei:                cross priv_mode_u, mstatus_mie, mstatus_sie, stvec_mode, mideleg_mei_zero, mie_meie, mip_meip;
    cp_user_sei:                cross priv_mode_u, mstatus_mie, mstatus_sie, stvec_mode, mideleg_sei, mie_seie, mip_seip;
    cp_wfi_timeout_u:           cross priv_mode_u, wfi, mstatus_mie, mstatus_sie, mideleg_ones, mstatus_tw_one, mie_mtie, timeout;
endgroup

function void interruptss_sample(int hart, int issue, ins_t ins);
    InterruptsS_cg.sample(ins);

    // $display("PC: %h Instr: %s\n  priv_mode=%b, mstatus.mie=%b mstatus.sie=%b mie=%h mideleg=%h mip=%h",
    //         ins.current.pc_rdata, ins.current.disass,
    //         ins.prev.mode, ins.current.csr[12'h300][3], ins.current.csr[12'h300][1],
    //         ins.current.csr[12'h304][11:0], ins.current.csr[12'h303][11:0], ins.current.csr[12'h344][11:0]);
    // $display("  priv_mode_s: %b wfi = %b, mstatus_mie %b (prev %b) mstatus_sie %b mideleg %h mstatus_tw %b mie %h mip %h",
    //             ins.prev.mode == 2'b01,
    //             ins.current.insn == 32'b0001000_00101_00000_000_00000_1110011,
    //             ins.current.csr[12'h300][3],
    //             ins.prev.csr[12'h300][3],
    //             ins.current.csr[12'h300][1],
    //             ins.current.csr[12'h303][15:0],
    //             ins.current.csr[12'h300][21],
    //             ins.current.csr[12'h304][15:0],
    //             ins.current.csr[12'h344][15:0]
    //         );
endfunction
