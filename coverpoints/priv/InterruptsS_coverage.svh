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

    mstatus_mie: coverpoint ins.prev.csr[CSR_MSTATUS][3]  {
        // autofill 0/1
    }
    mstatus_mie_zero: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
        bins zero = {0};
    }
    mstatus_mie_one: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
        bins one = {1};
    }
    mstatus_mpie: coverpoint ins.current.csr[CSR_MSTATUS][7] {
        // bins zero = {0};
        bins one = {1};
    }
    mstatus_sie: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        // autofill 0/1
    }
    mstatus_sie_one: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        bins one = {1};
    }
    prev_mstatus_sie_zero: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        bins zero = {0};
    }
    prev_mstatus_sie_one: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        bins one = {1};
    }
    mstatus_tw:  coverpoint ins.current.csr[CSR_MSTATUS][21] {
        // autofill 0/1
    }
    mstatus_tw_one:  coverpoint ins.current.csr[CSR_MSTATUS][21] {
        bins one = {1};
    }
    mideleg_msi_zero: coverpoint ins.current.csr[CSR_MIDELEG][3] {
        bins zero = {0};
    }
    mideleg_mti_zero: coverpoint ins.current.csr[CSR_MIDELEG][7] {
        bins zero = {0};
    }
    mideleg_sei: coverpoint ins.current.csr[CSR_MIDELEG][9] {
        // autofill 0/1
    }
    mideleg_ssi: coverpoint ins.current.csr[CSR_MIDELEG][1] {
        // autofill 0/1
    }
    mideleg_mei_zero: coverpoint ins.current.csr[CSR_MIDELEG][11] {
        bins zero = {0};
    }
    mideleg_zeros: coverpoint ins.current.csr[CSR_MIDELEG][15:0] {
        bins zeros = {16'b0000000000000000}; // zeros in every field that is not tied to zero
    }
    mideleg_ones: coverpoint ins.current.csr[CSR_MIDELEG][15:0] {
        bins ones  = {16'b0000001000100010}; //  ones in every field that is not tied to zero (only supervisor delegable)
    }
    mideleg_ones_zeros: coverpoint ins.current.csr[CSR_MIDELEG][15:0] {
        bins ones  = {16'b0000001000100010}; //  ones in every field that is not tied to zero (only supervisor delegable)
        //bins zeros = {16'b0000000000000000}; // zeros in every field that is not tied to zero
    }
    mideleg_ones_zeros_real: coverpoint ins.current.csr[CSR_MIDELEG][15:0] {
        bins ones  = {16'b0000001000100010}; //  ones in every field that is not tied to zero (only supervisor delegable)
        bins zeros = {16'b0000000000000000}; // zeros in every field that is not tied to zero
    }
    mie_msie: coverpoint ins.current.csr[CSR_MIE][3] {
        // autofill 0/1
    }
    mie_msie_one: coverpoint ins.current.csr[CSR_MIE][3] {
        bins one = {1};
    }
    mie_mtie: coverpoint ins.current.csr[CSR_MIE][7] {
        // autofill 0/1
    }
    mie_seie: coverpoint ins.current.csr[CSR_MIE][9] {
        // autofill 0/1
    }
    mie_seie_one: coverpoint ins.current.csr[CSR_MIE][9] {
        bins one = {1};
    }
    mie_meie: coverpoint ins.current.csr[CSR_MIE][11] {
        // autofill 0/1
    }
    mie_meie_one: coverpoint ins.current.csr[CSR_MIE][11] {
        bins one = {1};
    }
    mie_mtie_one: coverpoint ins.current.csr[CSR_MIE][7] {
        bins one = {1};
    }
    mie_ones: coverpoint ins.current.csr[CSR_MIE][15:0] {
        wildcard bins ones = {16'b????1?1?1?1?1?1?}; // ones in every field that is not tied to zero
    }
    mip_msip: coverpoint ins.current.csr[CSR_MIP][3] {
        // autofill 0/1
    }
    mip_mtip: coverpoint ins.current.csr[CSR_MIP][7] {
        // autofill 0/1
    }
    mip_seip: coverpoint ins.current.csr[CSR_MIP][9] {
        // autofill 0/1
    }
    mip_meip: coverpoint ins.current.csr[CSR_MIP][11] {
        // autofill 0/1
    }
    mip_ssip_one: coverpoint ins.current.csr[CSR_MIP][1] {
        bins one = {1};
    }
    mip_msip_one: coverpoint ins.current.csr[CSR_MIP][3] {
        bins one = {1};
    }
    mip_stip_one: coverpoint ins.current.csr[CSR_MIP][5] {
        bins one = {1};
    }
    mip_mtip_one: coverpoint ins.current.csr[CSR_MIP][7] {
        bins one = {1};
    }
    mip_seip_one: coverpoint ins.current.csr[CSR_MIP][9] {
        bins one = {1};
    }
    prev_mip_seip_one: coverpoint ins.prev.csr[CSR_MIP][9] {
        bins one = {1};
    }
    mip_seip_rise: coverpoint ins.current.csr[CSR_MIP][9] {
        bins rise = (0 => 1);
    }
    mip_meip_one: coverpoint ins.current.csr[CSR_MIP][11] {
        bins one = {1};
    }
    mip_ones: coverpoint ins.current.csr[CSR_MIP][15:0] {
        wildcard bins ones = {16'b0000101010101010}; // ones in every field that is not tied to zero
    }
    // All S-mode interrupts set: {SEIP, STIP, SSIP}
    mip_ones_s: coverpoint {ins.current.csr[CSR_MIP][9],   // SEIP
                        ins.current.csr[CSR_MIP][5],   // STIP
                        ins.current.csr[CSR_MIP][1]} { // SSIP
        bins all_s_set = {3'b111};  // All three S-mode interrupts set
    }
    // All M-mode interrupts set: {MEIP, MTIP, MSIP}
    mip_ones_m: coverpoint {ins.current.csr[CSR_MIP][11],  // MEIP
                        ins.current.csr[CSR_MIP][7],   // MTIP
                        ins.current.csr[CSR_MIP][3]} { // MSIP
        bins all_m_set = {3'b111};  // All three M-mode interrupts set
    }
    mie_walking: coverpoint {ins.current.csr[CSR_MIE][11],
                             ins.current.csr[CSR_MIE][9],
                             ins.current.csr[CSR_MIE][7],
                             ins.current.csr[CSR_MIE][5],
                             ins.current.csr[CSR_MIE][3],
                             ins.current.csr[CSR_MIE][1]} {
        bins meie = {6'b100000};
        bins seie = {6'b010000};
        bins mtie = {6'b001000};
        bins stie = {6'b000100};
        bins msie = {6'b000010};
        bins ssie = {6'b000001};
    }
    mie_walking_s: coverpoint {ins.current.csr[CSR_MIE][9],
                             ins.current.csr[CSR_MIE][5],
                             ins.current.csr[CSR_MIE][1]} {
        bins seie = {3'b100};
        bins stie = {3'b010};
        bins ssie = {3'b001};
    }
    mip_walking: coverpoint {ins.current.csr[CSR_MIP][11],
                             ins.current.csr[CSR_MIP][9],
                             ins.current.csr[CSR_MIP][7],
                             ins.current.csr[CSR_MIP][5],
                             ins.current.csr[CSR_MIP][3],
                             ins.current.csr[CSR_MIP][1]} {
        bins meip = {6'b100000};
        bins seip = {6'b010000};
        bins mtip = {6'b001000};
        bins stip = {6'b000100};
        bins msip = {6'b000010};
        bins ssip = {6'b000001};
    }
    mip_walking_s: coverpoint {ins.current.csr[CSR_MIP][9],
                             ins.current.csr[CSR_MIP][5],
                             ins.current.csr[CSR_MIP][1]} {
        bins seip = {3'b100};
        bins stip = {3'b010};
        bins ssip = {3'b001};
    }
    mip_walking_m: coverpoint {ins.current.csr[CSR_MIP][11],
                             ins.current.csr[CSR_MIP][7],
                             ins.current.csr[CSR_MIP][3]} {
        bins meip = {3'b100};
        bins mtip = {3'b010};
        bins msip = {3'b001};
    }
    // Matched pairs only: mismatched mip/mie bits won't trigger a trap, so MRET (M->S transition) won't occur.
    mip_mie_matched_m: coverpoint {ins.current.csr[CSR_MIP][11], ins.current.csr[CSR_MIP][7], ins.current.csr[CSR_MIP][3],
                               ins.current.csr[CSR_MIE][11], ins.current.csr[CSR_MIE][7], ins.current.csr[CSR_MIE][3]} {
        bins msip_msie = {6'b001001};  // MSIP=1, MSIE=1
        bins mtip_mtie = {6'b010010};  // MTIP=1, MTIE=1
        bins meip_meie = {6'b100100};  // MEIP=1, MEIE=1
    }
    // Check if instruction is MRET
    mret_insn: coverpoint ins.current.insn {
        bins mret = {32'h30200073};
    }
    sret_insn: coverpoint ins.current.insn {
        bins sret = {32'h10200073};
    }
    // Check if mstatus.MPP is 01 (supervisor mode)
    mstatus_mpp_s: coverpoint ins.current.csr[CSR_MSTATUS][12:11] {
        bins s_mode = {2'b01};
    }
    mstatus_mpp_u: coverpoint ins.current.csr[CSR_MSTATUS][12:11] {
        bins u_mode = {2'b00};
    }
    sstatus_spp_u: coverpoint ins.current.csr[CSR_SSTATUS][8] {
        bins u_mode = {1'b0};
    }
    mie_s_ones: coverpoint {ins.current.csr[CSR_MIE][9],
                            ins.current.csr[CSR_MIE][5],
                            ins.current.csr[CSR_MIE][1]} {
        bins ones = {3'b111};
    }
    mie_m_walking: coverpoint {ins.current.csr[CSR_MIE][11],
                               ins.current.csr[CSR_MIE][7],
                               ins.current.csr[CSR_MIE][3]} {
        bins meie = {3'b100};
        bins mtie = {3'b010};
        bins msie = {3'b001};
    }
    mie_s_walking: coverpoint {ins.current.csr[CSR_MIE][9],
                               ins.current.csr[CSR_MIE][5],
                               ins.current.csr[CSR_MIE][1]} {
        bins seie = {3'b100};
        bins stie = {3'b010};
        bins ssie = {3'b001};
    }
    mie_combinations: coverpoint {ins.current.csr[CSR_MIE][11],
                                  ins.current.csr[CSR_MIE][9],
                                  ins.current.csr[CSR_MIE][7],
                                  ins.current.csr[CSR_MIE][5],
                                  ins.current.csr[CSR_MIE][3],
                                  ins.current.csr[CSR_MIE][1]} {
        // auto fills all 2^6 combinations
    }
    // S-mode enable combinations: {SEIE, STIE, SSIE}
    mie_combinations_s: coverpoint {ins.current.csr[CSR_MIE][9],  // SEIE
                                ins.current.csr[CSR_MIE][5],  // STIE
                                ins.current.csr[CSR_MIE][1]} { // SSIE
        bins combo_000 = {3'b000};  // No enables (valid - interrupts pending but not enabled)
        bins combo_001 = {3'b001};
        bins combo_010 = {3'b010};
        bins combo_011 = {3'b011};
        bins combo_100 = {3'b100};
        bins combo_101 = {3'b101};
        bins combo_110 = {3'b110};
        bins combo_111 = {3'b111};
    }
    // M-mode enable combinations: {MEIE, MTIE, MSIE}
    mie_combinations_m: coverpoint {ins.current.csr[CSR_MIE][11], // MEIE
                                    ins.current.csr[CSR_MIE][7],  // MTIE
                                    ins.current.csr[CSR_MIE][3]} { // MSIE
        // bins combo_000 = {3'b000};  // Remove - no enables = no interrupt = no MRET
        bins combo_001 = {3'b001};  // MSIE only
        bins combo_010 = {3'b010};  // MTIE only
        bins combo_011 = {3'b011};
        bins combo_100 = {3'b100};  // MEIE only
        bins combo_101 = {3'b101};
        bins combo_110 = {3'b110};
        bins combo_111 = {3'b111};
    }
    mip_combinations: coverpoint {ins.current.csr[CSR_MIP][11],
                                  ins.current.csr[CSR_MIP][9],
                                  ins.current.csr[CSR_MIP][7],
                                  ins.current.csr[CSR_MIP][5],
                                  ins.current.csr[CSR_MIP][3],
                                  ins.current.csr[CSR_MIP][1]} {
        // auto fills all 2^6 combinations
    }
    // S-mode priority: combinations of SSIP, STIP, SEIP (2^3 = 8 combinations)
    mip_combinations_s: coverpoint {ins.current.csr[CSR_MIP][9],  // SEIP
                                    ins.current.csr[CSR_MIP][5],  // STIP
                                    ins.current.csr[CSR_MIP][1]} { // SSIP
        bins combo_000 = {3'b000};
        bins combo_001 = {3'b001};  // SSIP only
        bins combo_010 = {3'b010};  // STIP only
        bins combo_011 = {3'b011};  // SSIP+STIP
        bins combo_100 = {3'b100};  // SEIP only
        bins combo_101 = {3'b101};  // SSIP+SEIP
        bins combo_110 = {3'b110};  // STIP+SEIP
        bins combo_111 = {3'b111};  // All three
    }
    mip_combinations_m: coverpoint {ins.current.csr[CSR_MIP][11], // MEIP
                                    ins.current.csr[CSR_MIP][7],  // MTIP
                                    ins.current.csr[CSR_MIP][3]} { // MSIP
        // bins combo_000 = {3'b000}; // removing this because this is not an interrupt so mret would not execute
        bins combo_001 = {3'b001};  // MSIP only
        bins combo_010 = {3'b010};  // MTIP only
        bins combo_011 = {3'b011};  // MSIP+MTIP
        bins combo_100 = {3'b100};  // MEIP only
        bins combo_101 = {3'b101};  // MSIP+MEIP
        bins combo_110 = {3'b110};  // MTIP+MEIP
        bins combo_111 = {3'b111};  // All three
    }
    mideleg_combinations: coverpoint {ins.current.csr[CSR_MIDELEG][9],
                                      ins.current.csr[CSR_MIDELEG][5],
                                      ins.current.csr[CSR_MIDELEG][1]} {
        // auto fills all 2^3 combinations (assuming only supervisor interrupts are delegable)
    }
    // S-mode sampling: SEIP must be delegated (highest priority; traps to M-mode first otherwise).
    // Only combinations with SEIE delegated (bit 9 set) are valid for S-mode entry.
    // Priority order: SEIP > SSIP > STIP
    mideleg_combinations_s: coverpoint {ins.current.csr[CSR_MIDELEG][9],
                                        ins.current.csr[CSR_MIDELEG][5],
                                        ins.current.csr[CSR_MIDELEG][1]} {
        bins combo_100 = {3'b100};  // SEIE only
        bins combo_101 = {3'b101};  // SSIE+SEIE
        bins combo_110 = {3'b110};  // STIE+SEIE
        bins combo_111 = {3'b111};  // All delegated
    }

    // Patterns where at least one S-interrupt is NOT delegated (for M-mode sampling)
    mideleg_combinations_m: coverpoint {ins.current.csr[CSR_MIDELEG][9],
                                        ins.current.csr[CSR_MIDELEG][5],
                                        ins.current.csr[CSR_MIDELEG][1]} {
        bins combo_000 = {3'b000};  // None delegated
        bins combo_001 = {3'b001};  // SSIE only (STIP/SEIP not delegated)
        bins combo_010 = {3'b010};  // STIE only (SSIP/SEIP not delegated)
        bins combo_011 = {3'b011};  // SSIE+STIE (SEIP not delegated)
        bins combo_100 = {3'b100};  // SEIE only (SSIP/STIP not delegated)
        bins combo_101 = {3'b101};  // SSIE+SEIE (STIP not delegated)
        bins combo_110 = {3'b110};  // STIE+SEIE (SSIP not delegated)
    }
    mip_mie_eq: coverpoint (ins.current.csr[CSR_MIE][11:0] == ins.current.csr[CSR_MIP][11:0]) {
        bins equal = {1};
    }
    // S-mode: Check if S-mode interrupt bits match
    mip_mie_eq_s: coverpoint ({ins.current.csr[CSR_MIP][9], ins.current.csr[CSR_MIP][5], ins.current.csr[CSR_MIP][1]} ==
                            {ins.current.csr[CSR_MIE][9], ins.current.csr[CSR_MIE][5], ins.current.csr[CSR_MIE][1]}) {
        bins equal = {1};
    }

    // M-mode: Check if M-mode interrupt bits match
    mip_mie_eq_m: coverpoint ({ins.current.csr[CSR_MIP][11], ins.current.csr[CSR_MIP][7], ins.current.csr[CSR_MIP][3]} ==
                            {ins.current.csr[CSR_MIE][11], ins.current.csr[CSR_MIE][7], ins.current.csr[CSR_MIE][3]}) {
        bins equal = {1};
    }
    mideleg_mie_eq: coverpoint (ins.current.csr[CSR_MIDELEG][11:0] == ins.current.csr[CSR_MIP][11:0]) {
        bins equal = {1};
    }
    // S-mode: Priority among delegated interrupts
    // Exclude combo_000 (nothing enabled = no interrupt)
    mideleg_combinations_delegated: coverpoint {ins.current.csr[CSR_MIDELEG][9],
                                                ins.current.csr[CSR_MIDELEG][5],
                                                ins.current.csr[CSR_MIDELEG][1]} {
        bins combo_001 = {3'b001};  // SSIE only
        bins combo_010 = {3'b010};  // STIE only
        bins combo_011 = {3'b011};  // SSIE+STIE
        bins combo_100 = {3'b100};  // SEIE only
        bins combo_101 = {3'b101};  // SSIE+SEIE
        bins combo_110 = {3'b110};  // STIE+SEIE
        bins combo_111 = {3'b111};  // All
    }

    // Check mideleg == mie (only S-mode bits)
    mideleg_mie_eq_s: coverpoint ({ins.current.csr[CSR_MIDELEG][9], ins.current.csr[CSR_MIDELEG][5], ins.current.csr[CSR_MIDELEG][1]} ==
                                {ins.current.csr[CSR_MIE][9], ins.current.csr[CSR_MIE][5], ins.current.csr[CSR_MIE][1]}) {
        bins equal = {1};
    }
    stvec_mode: coverpoint ins.current.csr[CSR_STVEC][1:0] {
        bins direct   = {2'b00};
        bins vector   = {2'b01};
    }
    stvec_vectored: coverpoint ins.current.csr[CSR_STVEC][1:0] {
        bins vector   = {2'b01};
    }
    mtvec_direct: coverpoint ins.current.csr[CSR_MTVEC][1:0] {
        bins direct   = {2'b00};
    }
    mtvec_vectored: coverpoint ins.current.csr[CSR_MTVEC][1:0] {
        bins vector   = {2'b01};
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    csrrs: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    csrrc: coverpoint ins.current.insn {
        wildcard bins csrrc = {CSRRC};
    }
    write_mip_seip: coverpoint ins.current.rs1_val[9] iff (ins.current.insn[31:20] == CSR_MIP) {
        bins write_seip = {1};
    }
    sip_seip_one: coverpoint ins.current.csr[CSR_SIP][9] {
        bins one = {1};
    }
    write_sip_ssip: coverpoint ins.current.rs1_val[1] iff (ins.current.insn[31:20] == CSR_SIP) {
        bins write_ssip = {1};
    }
    sip_ssip_one: coverpoint ins.current.csr[CSR_SIP][1] {
        bins one = {1};
    }
    write_sstatus_sie: coverpoint ins.current.rs1_val[1] iff ( ins.current.insn[31:20] == CSR_SSTATUS) {
        bins write_sie = {1};
    }
    sstatus_sie: coverpoint ins.current.csr[CSR_SSTATUS][1] {
        bins one = {1};
        bins zero = {0};
    }
    write_mstatus_mie: coverpoint ins.current.rs1_val[3] iff ( ins.current.insn[31:20] == CSR_MSTATUS) {
        bins write_mie = {1};
    }
    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }
    timeout: coverpoint ins.current.csr[CSR_MIP][7] iff (ins.trap == 1) {
        bins no_timer_int = {0};
    }
    mstatus_tw_zero: coverpoint ins.current.csr[CSR_MSTATUS][21] {
        bins zero = {0};
    }
    mideleg_sei_zero: coverpoint ins.current.csr[CSR_MIDELEG][9] {
        bins zero = {0};
    }
    mideleg_sei_one: coverpoint ins.current.csr[CSR_MIDELEG][9] {
        bins one = {1};
    }
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

    // S-mode tests
    cp_trigger_sti_s:            cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones, mip_stip_one;
    cp_trigger_sti_m:            cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_zeros, mip_stip_one;
    cp_trigger_ssi_mip:          cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones, mip_ssip_one;
    cp_trigger_ssi_mip_m:        cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, mie_ones, mideleg_zeros, mip_ssip_one;
    cp_trigger_ssi_sip:          cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones, sip_ssip_one, csrrs, write_sip_ssip;
    cp_trigger_sei:              cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones, mip_seip_one;
    cp_trigger_sei_m:            cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_zeros, mip_seip_one;
    cp_trigger_sei_seip:         cross priv_mode_s, mstatus_mie_zero, mstatus_sie, mie_ones, mideleg_ones, sip_seip_one;
    cp_trigger_changingtos_sti:  cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_zero, mie_ones, mideleg_ones, mip_stip_one, sstatus_sie;
    cp_trigger_changingtos_ssi:  cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_zero, mie_ones, mideleg_ones, mip_ssip_one, sstatus_sie;
    cp_trigger_changingtos_sei:  cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_zero, mie_ones, mideleg_ones, mip_seip_one, sstatus_sie;
    cp_interrupts_s:             cross priv_mode_s, mstatus_mie_zero, mideleg_ones, mtvec_direct, mip_walking_s, mie_walking_s;
    cp_interrupts_s_m:           cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, mideleg_zeros, mtvec_direct, mip_mie_matched_m;
    cp_vectored_s:               cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_ones, mideleg_ones, stvec_mode, mip_walking_s;
    cp_vectored_s_m:             cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_ones, mideleg_ones, stvec_mode, mip_walking_m;

    // S-mode priority tests
    cp_priority_mip_s:           cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mip_combinations_s, mie_ones, mideleg_ones;
    cp_priority_mip_s_m:         cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, prev_mstatus_sie_one, mip_combinations_m, mie_ones, mideleg_zeros;
    cp_priority_mie_s:           cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_combinations_s, mip_ones_s, mideleg_ones;
    cp_priority_mie_s_m:         cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_combinations_m, mip_ones_m, mideleg_zeros;
    cp_priority_both_s:          cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_combinations_s, mip_mie_eq_s, mideleg_ones;
    cp_priority_both_m:          cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, prev_mstatus_sie_one, mie_combinations_m, mip_mie_eq_m, mideleg_zeros;
    cp_priority_mideleg_m:       cross priv_mode_m, mret_insn, mstatus_mpp_s, mstatus_mie_zero, prev_mstatus_sie_one, mideleg_combinations_m, mip_ones_s, mie_ones;
    cp_priority_mideleg_s:       cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mideleg_combinations_s, mip_ones_s, mie_ones;
    cp_priority_mideleg_s_eq:    cross priv_mode_s, mstatus_mie_zero, prev_mstatus_sie_one, mideleg_combinations_delegated, mip_ones_s, mideleg_mie_eq_s;
    cp_wfi_s:                    cross priv_mode_s, wfi, mstatus_mie, mstatus_sie, mideleg_ones_zeros_real, mstatus_tw, mie_mtie_one;
    cp_wfi_timeout_s:            cross priv_mode_m, mstatus_mie, mstatus_sie, mideleg_ones_zeros_real, mstatus_tw_one, mie_mtie;

    // M-mode tests
    cp_interrupts_m:            cross priv_mode_m, mstatus_mie, mtvec_direct, mideleg_ones_zeros_real, mip_walking, mie_walking;
    cp_vectored_m:              cross priv_mode_m, mstatus_mie_one, mtvec_vectored, mideleg_zeros, mip_walking_s, mie_s_ones;
    cp_priority_mip_m:          cross priv_mode_m, mie_ones, mideleg_zeros, mip_combinations;
    cp_priority_mie_m:          cross priv_mode_m, mip_ones, mideleg_zeros, mie_combinations;
    cp_wfi_m:                   cross priv_mode_m, wfi, mstatus_mie, mstatus_sie, mideleg_ones, mstatus_tw, mie_mtie_one; // NOTE: wfi still exits early so doesn't work
    cp_trigger_mti_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_mtip_one, csrrs, write_mstatus_mie;
    cp_trigger_ssi_sip_m:       cross priv_mode_m, mstatus_mie, mie_ones, mideleg_ssi, csrrs, write_sip_ssip;
    cp_trigger_msi_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_msip_one, csrrs, write_mstatus_mie;
    cp_trigger_mei_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_meip_one, csrrs, write_mstatus_mie;
    cp_trigger_sti_M_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_stip_one, csrrs, write_mstatus_mie;
    cp_trigger_ssi_M_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_ssip_one, csrrs, write_mstatus_mie;
    cp_trigger_sei_M_m:           cross priv_mode_m, mideleg_zeros, mie_ones, mip_seip_one, csrrs, write_mstatus_mie;
    cp_sei1:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, s_ext_intr_low, csrrw, write_mip_seip;
    cp_sei2:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, s_ext_intr_low, csrrs, write_mip_seip;
    cp_sei3:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, s_ext_intr_high;
    cp_sei4:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, prev_mip_seip_one, s_ext_intr_low,  csrrc, write_mip_seip;
    cp_sei5:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, prev_mip_seip_one, s_ext_intr_high, csrrc, write_mip_seip;
    cp_sei6_7:                  cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, s_ext_intr, mip_seip;
    cp_global_ie:               cross priv_mode_m, mstatus_mie, mstatus_sie, mip_walking_m, mip_mie_eq;

    // U-mode tests
    cp_user_mti:                cross priv_mode_m, mret_insn, mstatus_mpp_u, mstatus_mie_zero, mstatus_sie, stvec_mode, mideleg_mti_zero, mie_mtie_one, mip_mtip;
    cp_user_mti_m:              cross priv_mode_m, mstatus_mie_one, mstatus_sie, stvec_mode, mideleg_mti_zero, mie_mtie_one, mip_mtip;
    cp_user_msi:                cross priv_mode_m, mret_insn, mstatus_mpp_u, mstatus_mie_zero, mstatus_sie, stvec_mode, mideleg_msi_zero, mie_msie_one, mip_msip;
    cp_user_msi_m:              cross priv_mode_m, mstatus_mie_one, mstatus_sie, stvec_mode, mideleg_msi_zero, mie_msie_one, mip_msip;
    cp_user_mei:                cross priv_mode_m, mret_insn, mstatus_mpp_u, mstatus_mie_zero, mstatus_sie, stvec_mode, mideleg_mei_zero, mie_meie_one, mip_meip;
    cp_user_mei_m:              cross priv_mode_m, mstatus_mie_one, mstatus_sie, stvec_mode, mideleg_mei_zero, mie_meie_one, mip_meip;
    // Need to split into S-mode for delegated and M-mode when not
    // Not delegated: Trap to M-mode from U-mode
    cp_user_sei_m_nd: cross priv_mode_m, mret_insn, mstatus_mpp_u, mstatus_mie_zero, mstatus_sie, stvec_mode, mideleg_sei_zero, mie_seie_one, mip_seip;
    // Delegated: Trap to S-mode from U-mode
    cp_user_sei_s_d: cross priv_mode_s, sret_insn, sstatus_spp_u, mstatus_mie_zero, mstatus_sie, stvec_mode, mideleg_sei_one, mie_seie_one, mip_seip;
    // MIE=1, not delegated: M-mode
    cp_user_sei_m: cross priv_mode_m, mstatus_mie_one, mstatus_sie, stvec_mode, mideleg_sei_zero, mie_seie_one, mip_seip;
    // MIE=1, delegated: S-mode
    cp_user_sei_s: cross priv_mode_s, sret_insn, sstatus_spp_u, mstatus_mie_one, mstatus_sie, stvec_mode, mideleg_sei_one, mie_seie_one, mip_seip;
    cp_wfi_u: cross priv_mode_m, mstatus_mie, mstatus_sie, mideleg_ones_zeros_real, mstatus_tw, mie_mtie_one;
    cp_wfi_timeout_u: cross priv_mode_m, mstatus_mie, mstatus_sie, mideleg_ones, mstatus_tw_one, mie_mtie_one;

endgroup

function void interruptss_sample(int hart, int issue, ins_t ins);
    InterruptsS_cg.sample(ins);

    // $display("PC: %h Instr: %s\n  priv_mode=%b, mstatus.mie=%b mstatus.sie=%b mie=%h mideleg=%h mip=%h",
    //         ins.current.pc_rdata, ins.current.disass,
    //         ins.prev.mode, ins.current.csr[CSR_MSTATUS][3], ins.current.csr[CSR_MSTATUS][1],
    //         ins.current.csr[CSR_MIE][11:0], ins.current.csr[CSR_MIDELEG][11:0], ins.current.csr[CSR_MIP][11:0]);
    // $display("  priv_mode_s: %b wfi = %b, mstatus_mie %b (prev %b) mstatus_sie %b mideleg %h mstatus_tw %b mie %h mip %h",
    //             ins.prev.mode == 2'b01,
    //             ins.current.insn == WFI,
    //             ins.current.csr[CSR_MSTATUS][3],
    //             ins.prev.csr[CSR_MSTATUS][3],
    //             ins.current.csr[CSR_MSTATUS][1],
    //             ins.current.csr[CSR_MIDELEG][15:0],
    //             ins.current.csr[CSR_MSTATUS][21],
    //             ins.current.csr[CSR_MIE][15:0],
    //             ins.current.csr[CSR_MIP][15:0]
    //         );

    // $display("=== InterruptsS Debug ===");
    // $display("PC: %h Instr: %s priv_mode=%b", ins.current.pc_rdata, ins.current.disass, ins.prev.mode);
    // $display("  mstatus: MIE=%b SIE=%b TW=%b mode: %b",
    //             ins.prev.csr[CSR_MSTATUS][3], ins.prev.csr[CSR_MSTATUS][1],
    //             ins.current.csr[CSR_MSTATUS][21], {ins.prev.mode_virt, ins.prev.mode});
    // $display(" NEW mstatus: MIE=%b SPIE=%b SIE=%b TW=%b mode: %b",
    //         ins.current.csr[CSR_MSTATUS][3], ins.current.csr[CSR_MSTATUS][5],
    //         ins.current.csr[CSR_MSTATUS][1],
    //         ins.current.csr[CSR_MSTATUS][21], {ins.prev.mode_virt, ins.prev.mode});
    // $display("  mideleg: SEIE=%b STIE=%b SSIE=%b (full=%h)",
    //             ins.current.csr[CSR_MIDELEG][9], ins.current.csr[CSR_MIDELEG][5],
    //             ins.current.csr[CSR_MIDELEG][1], ins.current.csr[CSR_MIDELEG][15:0]);
    // $display("  mie: MEIE=%b SEIE=%b MTIE=%b STIE=%b MSIE=%b SSIE=%b (full=%h)",
    //             ins.current.csr[CSR_MIE][11], ins.current.csr[CSR_MIE][9],
    //             ins.current.csr[CSR_MIE][7], ins.current.csr[CSR_MIE][5],
    //             ins.current.csr[CSR_MIE][3], ins.current.csr[CSR_MIE][1],
    //             ins.current.csr[CSR_MIE][15:0]);
    // $display("  mip: MEIP=%b SEIP=%b MTIP=%b STIP=%b MSIP=%b SSIP=%b (full=%h)",
    //             ins.current.csr[CSR_MIP][11], ins.current.csr[CSR_MIP][9],
    //             ins.current.csr[CSR_MIP][7], ins.current.csr[CSR_MIP][5],
    //             ins.current.csr[CSR_MIP][3], ins.current.csr[CSR_MIP][1],
    //             ins.current.csr[CSR_MIP][15:0]);
    // $display("  sip: SEIP=%b STIP=%b SSIP=%b (full=%h)",
    //             ins.current.csr[CSR_SIP][9], ins.current.csr[CSR_SIP][5],
    //             ins.current.csr[CSR_SIP][1], ins.current.csr[CSR_SIP][15:0]);
    // $display("  mtvec.MODE=%b stvec.MODE=%b",
    //             ins.current.csr[CSR_MTVEC][1:0], ins.current.csr[CSR_STVEC][1:0]);
    // if (ins.current.trap)
    //     $display("  TRAP! mcause=%h scause=%h", ins.current.csr[CSR_MCAUSE], ins.current.csr[CSR_SCAUSE]);
    // $display("");
endfunction
