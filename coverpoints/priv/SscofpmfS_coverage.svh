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

`define COVER_SSCOFPMFS
covergroup SscofpmfS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_sscofpmf.svh"

    sip_lcofi: coverpoint ins.current.csr[CSR_SIP][13] {}
    sip_lcofi_one: coverpoint ins.current.csr[CSR_SIP][13] {
            bins one = {1};
    }
    sip_lcofi_zero: coverpoint ins.current.csr[CSR_SIP][13] {
            bins zero = {0};
    }

    sie_lcofi: coverpoint ins.current.csr[CSR_SIE][13] {}
    sstatus_sie_set: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins one = {1};
    }

    prev_mstatus_sie_one: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
            bins one = {1};
    }
    sie_state: coverpoint (ins.current.csr[CSR_SIE][15:0]) {
            bins all_zeros = {16'b0};
            // sie is WARL; unimplemented bits stay 0 after a write of all-1s, so "all
            // ones" means all ones in the bits this coverpoint actually cares about
            // (LCOFIE + the 3 standard S-mode enables), not a literal all-1s register.
            wildcard bins all_ones = {16'b??1???1???1???1?};
    }
    lcofi_ip_one: coverpoint ins.current.csr[CSR_MIP][13] {
            bins one  = {1};
    }
    mip_other_pending_s: coverpoint {ins.current.csr[CSR_MIP][9], ins.current.csr[CSR_MIP][5], ins.current.csr[CSR_MIP][1]} {
            bins none = {3'b000};
            bins seip = {3'b100};
            bins stip = {3'b010};
            bins ssip = {3'b001};
    }
    mideleg_s_ints: coverpoint {ins.current.csr[CSR_MIDELEG][13], ins.current.csr[CSR_MIDELEG][9],
                                ins.current.csr[CSR_MIDELEG][5],  ins.current.csr[CSR_MIDELEG][1]} {
            bins delegated = {4'b1111};
    }

    csr_access_pattern: coverpoint ins.current.insn {
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0);
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1);
        wildcard bins csrrs1    = {CSRRS} iff (ins.current.rs1_val == '1);
        wildcard bins csrrc1    = {CSRRC} iff (ins.current.rs1_val == '1);
        wildcard bins read_only = {CSRRS} iff (ins.current.rs1_val ==  0);
    }

    `ifdef UDB_MXLEN_64
        mhpmevent_inhibits_zero_state: coverpoint (ins.current.csr[CSR_MHPMEVENT3][62:58] == 5'b00000) {
                bins yes = {1};
        }
    `else
        mhpmevent_inhibits_zero_state: coverpoint (ins.current.csr[CSR_MHPMEVENT3H][30:26] == 5'b00000) {
                bins yes = {1};
        }
    `endif

    mcounteren_all_ones_state: coverpoint (ins.current.csr[CSR_MCOUNTEREN][31:3] == '1) {
            bins yes = {1};
    }

    mcounteren_stimulus_pattern_state: coverpoint (ins.current.csr[CSR_MCOUNTEREN][31:3]) {
        bins all_zeros = {29'h0};
        bins all_ones  = {29'h1FFFFFFF};
        bins walking[] = {29'h1, 29'h2, 29'h4, 29'h8, 29'h10, 29'h20, 29'h40, 29'h80,
                           29'h100, 29'h200, 29'h400, 29'h800, 29'h1000, 29'h2000,
                           29'h4000, 29'h8000, 29'h10000, 29'h20000, 29'h40000,
                           29'h80000, 29'h100000, 29'h200000, 29'h400000, 29'h800000,
                           29'h1000000, 29'h2000000, 29'h4000000, 29'h8000000, 29'h10000000};
    }

    of_stimulus_pattern: coverpoint (`OF_VEC) {
        bins all_zeros = {29'h0};
        bins all_ones  = {29'h1FFFFFFF};
        bins walking[] = {29'h1, 29'h2, 29'h4, 29'h8, 29'h10, 29'h20, 29'h40, 29'h80,
                           29'h100, 29'h200, 29'h400, 29'h800, 29'h1000, 29'h2000,
                           29'h4000, 29'h8000, 29'h10000, 29'h20000, 29'h40000,
                           29'h80000, 29'h100000, 29'h200000, 29'h400000, 29'h800000,
                           29'h1000000, 29'h2000000, 29'h4000000, 29'h8000000, 29'h10000000};
    }

    of_write_pattern: coverpoint (`OF_VEC) {
            bins all_ones     = {29'h1FFFFFFF};
            bins checker_even = {29'b1_0101_0101_0101_0101_0101_0101_0101}; // even-indexed OF bits set
            bins checker_odd  = {29'b0_1010_1010_1010_1010_1010_1010_1010}; // odd-indexed OF bits set
    }

    hpm_csr_target: coverpoint ins.current.insn[31:20] {
            bins scountovf   = {CSR_SCOUNTOVF};
    }

    lcofi_mideleg_one: coverpoint ins.current.csr[CSR_MIDELEG][13] {
            bins one  = {1};
    }

    cp_sinh_inhibits_smode:    cross priv_mode_s, mhpmevent_xinh_combos, mhpmevent_of_zero;
    cp_of_set_on_overflow:     cross priv_mode_s, sip_lcofi_one, mie_clear, mhpmevent_of_one, mhpmevent_inhibits_pattern_state;
    cp_overflow_hw_only:       cross priv_mode_s, mip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
    cp_lcofip_hw_only:         cross priv_mode_s, mhpmevent_of, sip_lcofi_zero;
    cp_scountovf_shadow:       cross priv_mode_s, mcounteren_all_ones_state, of_stimulus_pattern;
    cp_scountovf_mcounteren:   cross priv_mode_s, of_write_pattern, mcounteren_stimulus_pattern_state;
    cp_sscofpmf_access:        cross priv_mode_s, csr_access_pattern, hpm_csr_target;
    cp_lcofi_sip_s:            cross priv_mode_s, sstatus_sie_set, sie_lcofi, sip_lcofi, lcofi_mideleg_one;
    cp_lcofip_priority_s:      cross priv_mode_s, mhpmevent_inhibits_zero_state, prev_mstatus_sie_one, sie_state, lcofi_ip_one, mip_other_pending_s, mideleg_s_ints;
endgroup

function void sscofpmfs_sample(int hart, int issue, ins_t ins);
    SscofpmfS_cg.sample(ins);
endfunction
