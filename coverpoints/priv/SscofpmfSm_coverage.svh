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
covergroup SscofpmfSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_sscofpmf.svh"

    // M-mode access sweep also touches mhpmeventNh (RV32 only) -- kept local to Sm so the
    // own generator never exercises there.
    hpm_csr_target_m: coverpoint ins.current.insn[31:20] {
            bins scountovf   = {CSR_SCOUNTOVF};
            `ifdef UDB_MXLEN_32
                bins mhpmevent[] = {CSR_MHPMEVENT3H,  CSR_MHPMEVENT4H,  CSR_MHPMEVENT5H,
                                CSR_MHPMEVENT6H,  CSR_MHPMEVENT7H,  CSR_MHPMEVENT8H,
                                CSR_MHPMEVENT9H,  CSR_MHPMEVENT10H, CSR_MHPMEVENT11H,
                                CSR_MHPMEVENT12H, CSR_MHPMEVENT13H, CSR_MHPMEVENT14H,
                                CSR_MHPMEVENT15H, CSR_MHPMEVENT16H, CSR_MHPMEVENT17H,
                                CSR_MHPMEVENT18H, CSR_MHPMEVENT19H, CSR_MHPMEVENT20H,
                                CSR_MHPMEVENT21H, CSR_MHPMEVENT22H, CSR_MHPMEVENT23H,
                                CSR_MHPMEVENT24H, CSR_MHPMEVENT25H, CSR_MHPMEVENT26H,
                                CSR_MHPMEVENT27H, CSR_MHPMEVENT28H, CSR_MHPMEVENT29H,
                                CSR_MHPMEVENT30H, CSR_MHPMEVENT31H};
             `endif
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

    lcofi_ip_one: coverpoint ins.current.csr[CSR_MIP][13] {
            bins one  = {1};
    }
    lcofi_ip_zero: coverpoint ins.current.csr[CSR_MIP][13] {
                bins zero  = {0};
    }
    lcofi_ip: coverpoint ins.current.csr[CSR_MIP][13] {}
    lcofi_ie: coverpoint ins.current.csr[CSR_MIE][13] {}
    lcofi_mideleg: coverpoint ins.current.csr[CSR_MIDELEG][13] {}

    mstatus_mie_set: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
            bins one = {1};
    }
    mstatus_sie_set: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
            bins one = {1};
    }

    mie_state: coverpoint (ins.current.csr[CSR_MIE][15:0]) {
            bins all_zeros = {16'b0};
            wildcard bins all_ones = {16'b??1?1???1???1???};
    }
    mip_other_pending: coverpoint {ins.current.csr[CSR_MIP][11], ins.current.csr[CSR_MIP][7], ins.current.csr[CSR_MIP][3]} {
            bins none = {3'b000};
            bins meip = {3'b100};
            bins mtip = {3'b010};
            bins msip = {3'b001};
    }

    cp_minh_inhibits_mmode:    cross priv_mode_m, mhpmevent_xinh_combos, mhpmevent_of_zero;
    cp_of_set_on_overflow:     cross priv_mode_m, lcofi_ip_one, mie_clear, mhpmevent_inhibits_pattern_state, mhpmevent_of_one;
    cp_overflow_hw_only:       cross priv_mode_m, mip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
    cp_lcofip_hw_only:         cross priv_mode_m, mhpmevent_of, lcofi_ip_zero;
    cp_scountovf_mcounteren:   cross priv_mode_m, of_write_pattern, mcounteren_stimulus_pattern_state;
    cp_scountovf_shadow:       cross priv_mode_m, mcounteren_all_ones_state, of_stimulus_pattern;
    cp_sscofpmf_access:        cross priv_mode_m, csr_access_pattern, hpm_csr_target_m;
    cp_lcofi_m:                cross priv_mode_m, lcofi_ip, lcofi_ie, lcofi_mideleg, mstatus_mie_set, mstatus_sie_set;
    cp_lcofip_priority_m:      cross priv_mode_m, mhpmevent_inhibits_zero_state, mstatus_mie_set, mie_state, lcofi_ip_one, mip_other_pending;
endgroup

function void sscofpmfsm_sample(int hart, int issue, ins_t ins);
    SscofpmfSm_cg.sample(ins);
endfunction
