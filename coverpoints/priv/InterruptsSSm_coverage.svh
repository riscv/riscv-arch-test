///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Ellen Yu ellyu@hmc.edu July 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSSSM

covergroup InterruptsSSm_cg with function sample(ins_t ins);
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
    mstatus_sie: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        // autofill 0/1
    }
    mstatus_sie_one: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
        bins one = {1};
    }
    mstatus_tw:  coverpoint ins.current.csr[CSR_MSTATUS][21] {
        // autofill 0/1
    }
    mideleg_ssi: coverpoint ins.current.csr[CSR_MIDELEG][1] {
        // autofill 0/1
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
        bins ones  = {16'b0000101010101010}; //  ones in every field that is not tied to zero (both machine and supervisor delegable)
        bins zeros = {16'b0000000000000000}; // zeros in every field that is not tied to zero
    }
    mie_mtie: coverpoint ins.current.csr[CSR_MIE][7] {
        // autofill 0/1
    }
    mie_seie: coverpoint ins.current.csr[CSR_MIE][9] {
        // autofill 0/1
    }
    mie_meie: coverpoint ins.current.csr[CSR_MIE][11] {
        // autofill 0/1
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
    `ifdef SSTC_SUPPORTED
        prev_mip_stip_zero: coverpoint ins.prev.csr[CSR_MIP][5] {
            bins zero = {0};
    }
        prev_mip_stip_one: coverpoint ins.prev.csr[CSR_MIP][5] {
            bins one = {1};
    }
        write_mip: coverpoint ins.current.insn[31:20] {
            bins write_STIP = {CSR_MIP};
    }
        rs1_STIP: coverpoint ins.current.rs1_val {
            bins stip = {'h20};
    }
    `endif
    mip_mtip_one: coverpoint ins.current.csr[CSR_MIP][7] {
        bins one = {1};
    }
    mip_seip_one: coverpoint ins.current.csr[CSR_MIP][9] {
        bins one = {1};
    }
    prev_mip_seip_one: coverpoint ins.prev.csr[CSR_MIP][9] {
        bins one = {1};
    }
    mip_meip_one: coverpoint ins.current.csr[CSR_MIP][11] {
        bins one = {1};
    }
    mip_ones: coverpoint ins.current.csr[CSR_MIP][15:0] {
        wildcard bins ones = {16'b0000101010101010}; // ones in every field that is not tied to zero
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

    mie_s_ones: coverpoint {ins.current.csr[CSR_MIE][9],
                            ins.current.csr[CSR_MIE][5],
                            ins.current.csr[CSR_MIE][1]} {
        bins ones = {3'b111};
    }
    mie_combinations: coverpoint {ins.current.csr[CSR_MIE][11],
                                  ins.current.csr[CSR_MIE][9],
                                  ins.current.csr[CSR_MIE][7],
                                  ins.current.csr[CSR_MIE][5],
                                  ins.current.csr[CSR_MIE][3],
                                  ins.current.csr[CSR_MIE][1]} {
        // auto fills all 2^6 combinations
    }

    mip_combinations: coverpoint {ins.current.csr[CSR_MIP][11],
                                  ins.current.csr[CSR_MIP][9],
                                  ins.current.csr[CSR_MIP][7],
                                  ins.current.csr[CSR_MIP][5],
                                  ins.current.csr[CSR_MIP][3],
                                  ins.current.csr[CSR_MIP][1]} {
        // auto fills all 2^6 combinations
    }

    mip_mie_eq: coverpoint (ins.current.csr[CSR_MIE][11:0] == ins.current.csr[CSR_MIP][11:0]) {
        bins equal = {1};
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
    write_sip_ssip: coverpoint ins.current.rs1_val[1] iff (ins.current.insn[31:20] == CSR_SIP) {
        bins write_ssip = {1};
    }
    write_mstatus_mie: coverpoint ins.current.rs1_val[3] iff ( ins.current.insn[31:20] == CSR_MSTATUS) {
        bins write_mie = {1};
    }
    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }
    // Following coverpoint is dropped because RVVI doesn't yet tie s_ext_intr to anything.
    // For now, rely on test keeping external interrupt controller pin low when testing writes to mip.SEIP
    // Could restore if it is added to the RVVI spec later.
    //s_ext_intr_low: coverpoint ins.current.s_ext_intr {
    //    bins no_sei = {0};
    //}

    // main coverpoints

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
    cp_trigger_sti_M_m:         cross priv_mode_m, mideleg_zeros, mie_ones, mip_stip_one, csrrs, write_mstatus_mie;
    cp_trigger_ssi_M_m:         cross priv_mode_m, mideleg_zeros, mie_ones, mip_ssip_one, csrrs, write_mstatus_mie;
    cp_trigger_sei_M_m:         cross priv_mode_m, mideleg_zeros, mie_ones, mip_seip_one, csrrs, write_mstatus_mie;
    cp_sei1:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, /*s_ext_intr_low,*/ csrrw, write_mip_seip;
    cp_sei2:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, /*s_ext_intr_low,*/ csrrs, write_mip_seip;
    cp_sei3:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, mip_seip_one;
    cp_sei4:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, prev_mip_seip_one, /*s_ext_intr_low,*/ csrrc, write_mip_seip;
    cp_sei5:                    cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, prev_mip_seip_one, mip_seip_one, csrrc, write_mip_seip;
    cp_sei6_7:                  cross priv_mode_m, mideleg_zeros, mstatus_mie_zero, prev_mip_seip_one, mip_seip;
    cp_global_ie:               cross priv_mode_m, mstatus_mie, mstatus_sie, mip_walking_m, mip_mie_eq;
    `ifdef SSTC_SUPPORTED
        cp_stip_write_stimecmp_one: cross priv_mode_m, prev_mip_stip_zero, csrrs, write_mip, rs1_STIP;
        cp_stip_write_stimecmp_zero: cross priv_mode_m, prev_mip_stip_one, csrrc, write_mip, rs1_STIP;
    `endif


endgroup

function void interruptsssm_sample(int hart, int issue, ins_t ins);
    InterruptsSSm_cg.sample(ins);
endfunction
