///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written by Ayesha Anwar ayesha.anwaar2005@gmail.com
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSCOFPMFSM
`ifdef SSCOFPMF_SUPPORTED
    `ifndef RVMODEL_MHPMEVENT
        `error "RVMODEL_MHPMEVENT must be defined when SSCOFPMF_SUPPORTED"
    `endif
    `ifndef RVMODEL_MHPMCOUNTER
        `error "RVMODEL_MHPMCOUNTER must be defined when SSCOFPMF_SUPPORTED"
    `endif
`endif

covergroup SscofpmfSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    csr_access_pattern: coverpoint ins.current.insn {
        wildcard bins csrrw0   = {CSRRW} iff (ins.current.rs1_val ==  0); // write all zeros
        wildcard bins csrrw1   = {CSRRW} iff (ins.current.rs1_val == '1); // write all ones
        wildcard bins csrrs1   = {CSRRS} iff (ins.current.rs1_val == '1); // set all ones
        wildcard bins csrrc1   = {CSRRC} iff (ins.current.rs1_val == '1); // clear all ones
    }
    mhpmevent_of: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][63] {}
    mhpmevent_of_zero: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][63] {
            bins zero = {0};
    }
    mhpmevent_minh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][62] {}
    mhpmevent_minh_one: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][62] {
            bins one  = {1};  // inhibited     -> should NOT count in M-mode
    }
    hpmcounter_nonzero: coverpoint (ins.current.csr[RVMODEL_MHPMCOUNTER] != 0) {
            bins yes = {1};
            bins no  = {0};
    }
    mip_clear: coverpoint (ins.current.csr[CSR_MIP] == 0) {
            bins yes = {1};
    }
    mie_clear: coverpoint (ins.current.csr[CSR_MIE] == 0) {
            bins yes = {1};
    }
    mhpmcounter_all_ones: coverpoint (ins.current.csr[RVMODEL_MHPMCOUNTER] == {1'b1}) {
            bins yes = {1};
    }
    mhpmcounter_all_zeros: coverpoint (ins.current.csr[RVMODEL_MHPMCOUNTER] == {1'b0}) {
            bins yes = {1};
    }
    mhpmcounter_extremes: coverpoint ins.current.csr[RVMODEL_MHPMCOUNTER] {
            bins all_ones  = {'1};
            bins all_zeros = {'0};
    }
    // Pack the 29 OF bits (mhpmevent3..mhpmevent31) into one expression via macro
    `define OF_VEC {ins.current.csr[CSR_MHPMEVENTH31][63], ins.current.csr[CSR_MHPMEVENTH30][63], \
                     ins.current.csr[CSR_MHPMEVENTH29][63], ins.current.csr[CSR_MHPMEVENTH28][63], \
                     ins.current.csr[CSR_MHPMEVENTH27][63], ins.current.csr[CSR_MHPMEVENTH26][63], \
                     ins.current.csr[CSR_MHPMEVENTH25][63], ins.current.csr[CSR_MHPMEVENTH24][63], \
                     ins.current.csr[CSR_MHPMEVENTH23][63], ins.current.csr[CSR_MHPMEVENTH22][63], \
                     ins.current.csr[CSR_MHPMEVENTH21][63], ins.current.csr[CSR_MHPMEVENTH20][63], \
                     ins.current.csr[CSR_MHPMEVENTH19][63], ins.current.csr[CSR_MHPMEVENTH18][63], \
                     ins.current.csr[CSR_MHPMEVENTH17][63], ins.current.csr[CSR_MHPMEVENTH16][63], \
                     ins.current.csr[CSR_MHPMEVENTH15][63], ins.current.csr[CSR_MHPMEVENTH14][63], \
                     ins.current.csr[CSR_MHPMEVENTH13][63], ins.current.csr[CSR_MHPMEVENTH12][63], \
                     ins.current.csr[CSR_MHPMEVENTH11][63], ins.current.csr[CSR_MHPMEVENTH10][63], \
                     ins.current.csr[CSR_MHPMEVENTH9][63],  ins.current.csr[CSR_MHPMEVENTH8][63], \
                     ins.current.csr[CSR_MHPMEVENTH7][63],  ins.current.csr[CSR_MHPMEVENTH6][63], \
                     ins.current.csr[CSR_MHPMEVENTH5][63],  ins.current.csr[CSR_MHPMEVENTH4][63], \
                     ins.current.csr[CSR_MHPMEVENTH3][63]}

    of_write_pattern: coverpoint (`OF_VEC) {
            bins all_ones     = {29'h1FFFFFFF};
            bins checker_even = {29'b1_0101_0101_0101_0101_0101_0101_0101}; // even-indexed OF bits set
            bins checker_odd  = {29'b0_1010_1010_1010_1010_1010_1010_1010}; // odd-indexed OF bits set
    }
    mcounteren_write_pattern: coverpoint $countones(ins.current.rs1_val[31:3])
                        iff (ins.current.insn[31:20] == CSR_MCOUNTEREN && (ins.current.insn ==? CSRRW || ins.current.insn ==? CSRRS || ins.current.insn ==? CSRRC)) {
            bins all_zeros   = {0};
            bins walking_one = {1};
            bins all_ones    = {29};
    }
    mhpmevent_all_zero: coverpoint ins.current.insn {
            wildcard bins write_zero = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT && ins.current.rs1_val == '0);
    }
    csrops: coverpoint ins.current.insn {
            wildcard bins csrw = {CSRRW};
            wildcard bins csrs = {CSRRS};
            wildcard bins csrc = {CSRRC};
    }

    mhpmevent_inhibits_all_set: coverpoint ins.current.insn {
            wildcard bins write_pattern = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT && ins.current.rs1_val[62:58] == 5'b11100);
    }
    hpm_csr_target: coverpoint ins.current.insn[31:20] {
            bins scountovf   = {CSR_SCOUNTOVF};
            bins mhpmevent[] = {CSR_MHPMEVENTH3,  CSR_MHPMEVENTH4,  CSR_MHPMEVENTH5,
                                CSR_MHPMEVENTH6,  CSR_MHPMEVENTH7,  CSR_MHPMEVENTH8,
                                CSR_MHPMEVENTH9,  CSR_MHPMEVENTH10, CSR_MHPMEVENTH11,
                                CSR_MHPMEVENTH12, CSR_MHPMEVENTH13, CSR_MHPMEVENTH14,
                                CSR_MHPMEVENTH15, CSR_MHPMEVENTH16, CSR_MHPMEVENTH17,
                                CSR_MHPMEVENTH18, CSR_MHPMEVENTH19, CSR_MHPMEVENTH20,
                                CSR_MHPMEVENTH21, CSR_MHPMEVENTH22, CSR_MHPMEVENTH23,
                                CSR_MHPMEVENTH24, CSR_MHPMEVENTH25, CSR_MHPMEVENTH26,
                                CSR_MHPMEVENTH27, CSR_MHPMEVENTH28, CSR_MHPMEVENTH29,
                                CSR_MHPMEVENTH30, CSR_MHPMEVENTH31};
    }
    lcofi_ip_one: coverpoint ins.current.csr[CSR_MIP][13] {
            bins one  = {1};
    }
    lcofi_ip_zero: coverpoint ins.current.csr[CSR_MIP][13] {
            bins zero = {0};
    }
    lcofi_ip:          coverpoint ins.current.csr[CSR_MIP][13] {}
    lcofi_ie:          coverpoint ins.current.csr[CSR_MIE][13] {}
    lcofi_mideleg:     coverpoint ins.current.csr[CSR_MIDELEG][13] {}
    lcofi_mideleg_one: coverpoint ins.current.csr[CSR_MIDELEG][13] {
            bins one  = {1};
    }
    lcofi_mideleg_zero: coverpoint ins.current.csr[CSR_MIDELEG][13] {
            bins zero = {0};
    }
    mstatus_mie_clear: coverpoint ins.current.csr[CSR_MSTATUS][3] {
            bins zero = {0};
    }
    mstatus_mie_set: coverpoint ins.current.csr[CSR_MSTATUS][3] {
            bins one = {1};
    }
    mstatus_sie_set: coverpoint ins.current.csr[CSR_MSTATUS][1] {
            bins one = {1};
    }
    sstatus_sie_set: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins one = {1};
    }
    mip_other_pending: coverpoint {ins.current.csr[CSR_MIP][11], ins.current.csr[CSR_MIP][7], ins.current.csr[CSR_MIP][3],
                                    ins.current.csr[CSR_MIP][9],  ins.current.csr[CSR_MIP][5], ins.current.csr[CSR_MIP][1]} {
            bins none = {6'b000000};
            bins meip = {6'b100000};
            bins mtip = {6'b010000};
            bins msip = {6'b001000};
            bins seip = {6'b000100};
            bins stip = {6'b000010};
            bins ssip = {6'b000001};
    }
    cp_mhpmevent_inhibit_bits: cross mhpmevent_minh, mhpmevent_sinh, mhpmevent_uinh;
    cp_minh_inhibits_mmode:    cross priv_mode_m, mhpmevent_minh, hpmcounter_nonzero, mhpmevent_of_zero ;
    cp_of_set_on_overflow:     cross priv_mode_m, mip_clear, mie_clear, mhpmevent_of;
    cp_overflow_hw_only:       cross priv_mode_m, mip_clear, mie_clear, mhpmcounter_extremes, mhpmevent_all_zero;
    cp_scountovf_mcounteren:   cross priv_mode_m, of_write_pattern, mcounteren_write_pattern ;
    cp_sscofpmf_access:        cross priv_mode_m, csr_access_pattern, hpm_csr_target ;
    cp_lcofi:                  cross priv_mode_m, lcofi_ip, lcofi_ie, lcofi_mideleg, lcofi_mideleg, mstatus_mie_clear, mstatus_sie_set;
    cp_lcofip_priority:        cross priv_mode_m, mstatus_mie_set, sstatus_sie_set, csrops,  lcofi_ip_one, mip_other_pending {ignore_bins not_csrw    = binsof(csrops.csrs) || binsof(csrops.csrc);}
endgroup

function void sscofpmfSm_sample(int hart, int issue, ins_t ins);
    SscofpmfSm_cg.sample(ins);
endfunction
