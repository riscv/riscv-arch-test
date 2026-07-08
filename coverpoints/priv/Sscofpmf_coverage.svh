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

`define COVER_SSCOFPMF
`ifdef SSCOFPMF_SUPPORTED
    `ifndef RVMODEL_MHPMEVENT
        `error "RVMODEL_MHPMEVENT must be defined when SSCOFPMF_SUPPORTED"
    `endif
    `ifndef RVMODEL_MHPMCOUNTER
        `error "RVMODEL_MHPMCOUNTER must be defined when SSCOFPMF_SUPPORTED"
    `endif
`endif

covergroup Sscofpmf_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    csr_access_pattern: coverpoint ins.current.insn {
        wildcard bins csrrw0   = {CSRRW} iff (ins.current.rs1_val ==  0); // write all zeros
        wildcard bins csrrw1   = {CSRRW} iff (ins.current.rs1_val == '1); // write all ones
        wildcard bins csrrs1   = {CSRRS} iff (ins.current.rs1_val == '1); // set all ones
        wildcard bins csrrc1   = {CSRRC} iff (ins.current.rs1_val == '1); // clear all ones
    }
    priv_mode_m_maybes_u: coverpoint {ins.current.mode_virt, ins.prev.mode} {
            bins M_mode = {3'b011};
            bins U_mode = {3'b000};
        `ifdef S_SUPPORTED
                bins S_mode = {3'b001};
        `endif
    }
    mhpmevent_of: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][63] {
            bins one  = {1};
            bins zero = {0};
    }
    mhpmevent_of_zero: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][63] {
            bins zero = {0};
    }
    mhpmevent_minh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][62] {
            bins one  = {1};  // inhibited     -> should NOT count in M-mode
            bins zero = {0};  // not inhibited -> should count in M-mode
    }
    mhpmevent_minh_one: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][62] {
            bins one  = {1};  // inhibited     -> should NOT count in M-mode
    }
    mhpmevent_sinh_one: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][61] {
            bins one  = {1};
    }
    mhpmevent_sinh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][61] {
            bins zero = {0};
            bins one  = {1};
    }
    mhpmevent_uinh_one: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][60] {
            bins one  = {1};
    }
    mhpmevent_uinh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][60] {
            bins zero = {0};
            bins one  = {1};
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
    mhpmevent_of_set_then_cleared: coverpoint {ins.prev.csr[RVMODEL_MHPMEVENT][63], ins.current.csr[RVMODEL_MHPMEVENT][63]} {
            bins set_then_clear = {2'b10};
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

    mcounteren_write_all_ones: coverpoint ins.current.insn {
                wildcard bins write_ones = {CSRRW} iff (ins.current.insn[31:20] == CSR_MCOUNTEREN &&
                                                  ins.current.rs1_val[31:3] == '1);
    }
    of_walking_one: coverpoint $clog2(`OF_VEC) iff ($onehot(`OF_VEC)) {
            bins b_of[] = {[0:28]};  // one bin per OF bit position (mhpmevent3..mhpmevent31 = 29 bits)
    }
    of_pattern_class: coverpoint $countones(`OF_VEC) {
            bins all_zeros   = {0};
            bins all_ones    = {29};
    }

    scountovf_of_match: coverpoint ((ins.current.csr[CSR_SCOUNTOVF][31:3] & ins.current.csr[CSR_MCOUNTEREN][31:3]) == (`OF_VEC & ins.current.csr[CSR_MCOUNTEREN][31:3])) {
            bins match = {1};
    }


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
            bins mcounteren  = {CSR_MCOUNTEREN};
            bins mhpmevent[] = {CSR_MHPMEVENT3,  CSR_MHPMEVENT4,  CSR_MHPMEVENT5,
                                CSR_MHPMEVENT6,  CSR_MHPMEVENT7,  CSR_MHPMEVENT8,
                                CSR_MHPMEVENT9,  CSR_MHPMEVENT10, CSR_MHPMEVENT11,
                                CSR_MHPMEVENT12, CSR_MHPMEVENT13, CSR_MHPMEVENT14,
                                CSR_MHPMEVENT15, CSR_MHPMEVENT16, CSR_MHPMEVENT17,
                                CSR_MHPMEVENT18, CSR_MHPMEVENT19, CSR_MHPMEVENT20,
                                CSR_MHPMEVENT21, CSR_MHPMEVENT22, CSR_MHPMEVENT23,
                                CSR_MHPMEVENT24, CSR_MHPMEVENT25, CSR_MHPMEVENT26,
                                CSR_MHPMEVENT27, CSR_MHPMEVENT28, CSR_MHPMEVENT29,
                                CSR_MHPMEVENT30, CSR_MHPMEVENT31};
    }
    lcofi_ip_one: coverpoint ins.current.csr[CSR_MIP][13] {
            bins one  = {1};
    }
    lcofi_ip_zero: coverpoint ins.current.csr[CSR_MIP][13] {
            bins zero = {0};
    }
    lcofi_ip: coverpoint ins.current.csr[CSR_MIP][13] {
            bins zero = {0};
            bins one  = {1};
    }
    lcofi_ie: coverpoint ins.current.csr[CSR_MIE][13] {
            bins zero = {0};
            bins one  = {1};
    }
    lcofi_mideleg: coverpoint ins.current.csr[CSR_MIDELEG][13] {
            bins zero = {0};
            bins one  = {1};
    }
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
    sstatus_sie_clear: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins zero = {0};
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
    cp_sinh_inhibits_smode:    cross priv_mode_s, mhpmevent_sinh, hpmcounter_nonzero, mhpmevent_of_zero ;
    cp_uinh_inhibits_umode:    cross priv_mode_u, mhpmevent_uinh, hpmcounter_nonzero, mhpmevent_of_zero ;
    cp_of_set_on_overflow:     cross priv_mode_m_maybes_u, mip_clear, mie_clear, mhpmevent_of, mhpmevent_minh_one, mhpmevent_sinh_one, mhpmevent_uinh_one;
    cp_overflow_hw_only:       cross priv_mode_m_maybes_u, mip_clear, mie_clear, mhpmcounter_extremes, mhpmevent_all_zero;
    cp_lcofip_hw_only:         cross priv_mode_s, mhpmevent_of_set_then_cleared;
    cp_scountovf_shadow:       cross priv_mode_s, mcounteren_write_all_ones, of_pattern_class, of_walking_one, scountovf_of_match;
    cp_scountovf_mcounteren:   cross priv_mode_m_maybes_u, of_write_pattern, mcounteren_write_pattern {ignore_bins u_mode = binsof(priv_mode_m_maybes_u.U_mode);}
    cp_sscofpmf_access:        cross priv_mode_m_maybes_u, csr_access_pattern, hpm_csr_target {ignore_bins u_mode = binsof(priv_mode_m_maybes_u.U_mode);}
    cp_lcofi:                  cross priv_mode_m_maybes_u, lcofi_ip, lcofi_ie, lcofi_mideleg, lcofi_mideleg, mstatus_mie_clear, mstatus_sie_set;
    cp_lcofi_sip_s:            cross priv_mode_s, sstatus_sie_set, lcofi_ie, lcofi_ip, lcofi_mideleg_one ;
    cp_lcofi_sip_u:            cross priv_mode_u, sstatus_sie_clear, lcofi_ie, lcofi_ip, lcofi_mideleg_one ;
    cp_lcofip_priority:        cross priv_mode_m_maybes_u, mstatus_mie_set, sstatus_sie_set, csrops,  lcofi_ip_one, mip_other_pending {ignore_bins not_csrw    = binsof(csrops.csrs) || binsof(csrops.csrc);}
endgroup

function void sscofpmf_sample(int hart, int issue, ins_t ins);
    Sscofpmf_cg.sample(ins);
endfunction
