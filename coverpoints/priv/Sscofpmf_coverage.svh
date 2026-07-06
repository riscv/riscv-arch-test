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

    priv_mode_m: coverpoint ins.current.mode {
            type_option.weight = 0;
            bins M_mode = {2'b11};
    }
    priv_mode_s: coverpoint ins.current.mode {
            type_option.weight = 0;
            bins S_mode = {2'b01};
    }
    priv_mode_u: coverpoint ins.current.mode {
            type_option.weight = 0;
            bins U_mode = {2'b00};
    }
    priv_mode_m_maybes_u: coverpoint {ins.current.mode_virt, ins.prev.mode} {
            bins M_mode = {3'b011};
            bins U_mode = {3'b000};
        `ifdef S_SUPPORTED
                bins S_mode = {3'b001};
        `endif
    }
    mhpmevent_of: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][63] {
            bins zero = {0};
            bins one  = {1};
    }
    mhpmevent_minh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][62] {
            bins zero = {0};  // not inhibited -> should count in M-mode
            bins one  = {1};  // inhibited     -> should NOT count in M-mode
    }
    mhpmevent_sinh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][61] {
            bins zero = {0};
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
    mhpmcounter_all_ones: coverpoint (ins.current.csr[RVMODEL_MHPMCOUNTER] == {64{1'b1}}) {
            bins yes = {1};
    }
    mhpmcounter_all_zeros: coverpoint (ins.current.csr[RVMODEL_MHPMCOUNTER] == 64'h0) {
            bins yes = {1};
    }
    mhpmcounter_extremes: coverpoint ins.current.csr[RVMODEL_MHPMCOUNTER] {
            bins all_ones  = {'1};
            bins all_zeros = {'0};
    }
    mhpmevent_of_set_then_cleared: coverpoint {ins.prev.csr[RVMODEL_MHPMEVENT][63], ins.current.csr[RVMODEL_MHPMEVENT][63]} {
            bins set_then_clear = {2'b10};
    }
    mip_lcofip_zero: coverpoint ins.current.csr[CSR_MIP][13] {
            bins zero = {0};
    }
    // Pack the 29 OF bits (mhpmevent3..mhpmevent31) into one expression via macro
    `define OF_VEC {ins.current.csr[CSR_MHPMEVENT31][63], ins.current.csr[CSR_MHPMEVENT30][63], \
                     ins.current.csr[CSR_MHPMEVENT29][63], ins.current.csr[CSR_MHPMEVENT28][63], \
                     ins.current.csr[CSR_MHPMEVENT27][63], ins.current.csr[CSR_MHPMEVENT26][63], \
                     ins.current.csr[CSR_MHPMEVENT25][63], ins.current.csr[CSR_MHPMEVENT24][63], \
                     ins.current.csr[CSR_MHPMEVENT23][63], ins.current.csr[CSR_MHPMEVENT22][63], \
                     ins.current.csr[CSR_MHPMEVENT21][63], ins.current.csr[CSR_MHPMEVENT20][63], \
                     ins.current.csr[CSR_MHPMEVENT19][63], ins.current.csr[CSR_MHPMEVENT18][63], \
                     ins.current.csr[CSR_MHPMEVENT17][63], ins.current.csr[CSR_MHPMEVENT16][63], \
                     ins.current.csr[CSR_MHPMEVENT15][63], ins.current.csr[CSR_MHPMEVENT14][63], \
                     ins.current.csr[CSR_MHPMEVENT13][63], ins.current.csr[CSR_MHPMEVENT12][63], \
                     ins.current.csr[CSR_MHPMEVENT11][63], ins.current.csr[CSR_MHPMEVENT10][63], \
                     ins.current.csr[CSR_MHPMEVENT9][63],  ins.current.csr[CSR_MHPMEVENT8][63], \
                     ins.current.csr[CSR_MHPMEVENT7][63],  ins.current.csr[CSR_MHPMEVENT6][63], \
                     ins.current.csr[CSR_MHPMEVENT5][63],  ins.current.csr[CSR_MHPMEVENT4][63], \
                     ins.current.csr[CSR_MHPMEVENT3][63]}

    mcounteren_all_ones: coverpoint (ins.current.csr[CSR_MCOUNTEREN] == '1) {
            bins yes = {1};
    }
    of_pattern_class: coverpoint $countones(`OF_VEC) {
            bins all_zeros   = {0};
            bins walking_one = {1};
            bins all_ones    = {29};
    }

    scountovf_of_match: coverpoint (ins.current.csr[CSR_SCOUNTOVF][31:3] == `OF_VEC) {
            bins match = {1};
    }


    of_write_pattern: coverpoint (`OF_VEC) {
            bins all_ones     = {29'h1FFFFFFF};
            bins checker_even = {29'b1_0101_0101_0101_0101_0101_0101_0101}; // even-indexed OF bits set
            bins checker_odd  = {29'b0_1010_1010_1010_1010_1010_1010_1010}; // odd-indexed OF bits set
    }
    mcounteren_hpm_pattern: coverpoint (ins.current.csr[CSR_MCOUNTEREN][31:3]) {
            bins all_zeros     = {29'h0};
            bins all_ones      = {29'h1FFFFFFF};
            bins walking_one[] = {29'h1,     29'h2,     29'h4,     29'h8,
                                29'h10,    29'h20,    29'h40,    29'h80,
                                29'h100,   29'h200,   29'h400,   29'h800,
                                29'h1000,  29'h2000,  29'h4000,  29'h8000,
                                29'h10000, 29'h20000, 29'h40000, 29'h80000,
                                29'h100000, 29'h200000, 29'h400000, 29'h800000,
                                29'h1000000, 29'h2000000, 29'h4000000, 29'h8000000,
                                29'h10000000};
    }
    csrops: coverpoint ins.current.insn {
            wildcard bins csrw = {CSRRW};
            wildcard bins csrs = {CSRRS};
            wildcard bins csrc = {CSRRC};
    }

    csr_write_value_pattern: coverpoint ins.current.rs1_val {
            bins all_ones  = {'1};
            bins all_zeros = {'0};
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
    mie_all_ones: coverpoint (ins.current.csr[CSR_MIE] == '1) {
            bins yes = {1};
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

    cp_minh_inhibits_mmode:  cross priv_mode_m, mhpmevent_minh, hpmcounter_nonzero, mhpmevent_of { ignore_bins of_one = binsof(mhpmevent_of.one); }
    cp_sinh_inhibits_smode:  cross priv_mode_s, mhpmevent_sinh, hpmcounter_nonzero, mhpmevent_of { ignore_bins of_one = binsof(mhpmevent_of.one); }
    cp_uinh_inhibits_umode:  cross priv_mode_u, mhpmevent_uinh, hpmcounter_nonzero, mhpmevent_of { ignore_bins of_one = binsof(mhpmevent_of.one); }
    cp_of_set_on_overflow:   cross priv_mode_m_maybes_u, mip_clear, mie_clear, mhpmevent_of { ignore_bins of_zero = binsof(mhpmevent_of.zero); }
    cp_overflow_hw_only:     cross priv_mode_m_maybes_u, mip_clear, mie_clear, mhpmcounter_extremes, mhpmevent_of { ignore_bins of_one = binsof(mhpmevent_of.one); }
    cp_lcofip_hw_only:       cross priv_mode_s, mhpmevent_of_set_then_cleared, mip_lcofip_zero;
    cp_scountovf_shadow:     cross priv_mode_s, mcounteren_all_ones, of_pattern_class, scountovf_of_match;
    cp_scountovf_mcounteren: cross priv_mode_m_maybes_u, of_write_pattern, mcounteren_hpm_pattern {ignore_bins u_mode = binsof(priv_mode_m_maybes_u.U_mode);}
    cp_sscofpmf_write:       cross priv_mode_m_maybes_u, csr_write_value_pattern, hpm_csr_target {
            ignore_bins u_mode = binsof(priv_mode_m_maybes_u.U_mode);
    }
    cp_sscofpmf_setclear:    cross priv_mode_m_maybes_u, csrops, hpm_csr_target {
            ignore_bins u_mode  = binsof(priv_mode_m_maybes_u.U_mode);
            ignore_bins no_write = binsof(csrops.csrw);  // csrw handled by the cross above
    }
    cp_lcofi:                cross priv_mode_m_maybes_u, lcofi_ip, lcofi_ie, lcofi_mideleg, mstatus_mie_clear, mstatus_sie_set;
    cp_lcofi_sip_s:          cross priv_mode_s, sstatus_sie_set, lcofi_ie, lcofi_ip, lcofi_mideleg { ignore_bins mideleg_zero = binsof(lcofi_mideleg.zero); }
    cp_lcofi_sip_u:          cross priv_mode_u, sstatus_sie_clear, lcofi_ie, lcofi_ip, lcofi_mideleg { ignore_bins mideleg_zero = binsof(lcofi_mideleg.zero); }
    cp_lcofip_priority:      cross priv_mode_m_maybes_u, mstatus_mie_set, sstatus_sie_set, mie_all_ones, lcofi_ip, mip_other_pending {
            ignore_bins lcofip_zero = binsof(lcofi_ip.zero);
    }



endgroup

function void sscofpmf_sample(int hart, int issue, ins_t ins);
    Sscofpmf_cg.sample(ins);
endfunction
