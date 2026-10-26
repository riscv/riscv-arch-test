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

// Sm tests are not part of a certificate without Sm (EXCLUDE_SM), so neither is their covergroup
`ifndef EXCLUDE_SM
covergroup Sscofpmf_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sscofpmf.svh"

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

    // csrr scountovf (csrrs rd, scountovf, x0)
    scountovf_read: coverpoint ins.current.insn {
        wildcard bins read = {CSRR} iff (ins.current.insn[31:20] == CSR_SCOUNTOVF);
    }

    csr_access_pattern: coverpoint ins.current.insn {
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0);
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1);
        wildcard bins csrrs1    = {CSRRS} iff (ins.current.rs1_val == '1);
        wildcard bins csrrc1    = {CSRRC} iff (ins.current.rs1_val == '1);
        wildcard bins read_only = {CSRRS} iff (ins.current.rs1_val ==  0);
    }

    `ifdef UDB_MXLEN_64
        mhpmevent_inhibits_zero_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT, `SSCOFPMF_MHPMEVENT)[62:58] == 5'b00000) {
                bins yes = {1};
        }
    `else
        mhpmevent_inhibits_zero_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH, `SSCOFPMF_MHPMEVENTH)[30:26] == 5'b00000) {
                bins yes = {1};
        }
    `endif

    mcounteren_all_ones_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "enable")[28:0] == '1) {
            bins yes = {1};
    }

    mcounteren_stimulus_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "enable")[28:0]) {
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

    lcofi_ip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "lcofip")[0] {
            bins one  = {1};
    }
    lcofi_ip_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "lcofip")[0] {
                bins zero  = {0};
    }
    lcofi_ip: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "lcofip")[0] {}
    lcofi_ie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "lcofie")[0] {}
    lcofi_mideleg: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "lcofip")[0] {}

    mstatus_mie_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
            bins one = {1};
    }

    mie_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")[15:0]) {
            bins all_zeros = {16'b0};
            wildcard bins all_ones = {16'b??1?1???1???1???};
    }
    mip_other_pending: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "meip")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mtip")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "msip")[0]} {
            bins none = {3'b000};
            `ifdef UDB_MEI_INTR_IMPL
            bins meip = {3'b100};
            `endif
            `ifdef UDB_MTI_INTR_IMPL
            bins mtip = {3'b010};
            `endif
            `ifdef UDB_MSI_INTR_IMPL
            bins msip = {3'b001};
            `endif
    }

    cp_minh_inhibits_mmode:    cross priv_mode_m, mhpmevent_xinh_combos, mhpmevent_of_zero;
    // The suite never leaves M-mode, so a pattern that inhibits M-mode counting cannot overflow.
    cp_of_set_on_overflow:     cross priv_mode_m, lcofi_ip_one, mie_clear, mhpmevent_inhibits_pattern_state, mhpmevent_of_one {
        ignore_bins self_inhibited = binsof(mhpmevent_inhibits_pattern_state.minh_only) ||
                                     binsof(mhpmevent_inhibits_pattern_state.msu_set);
    }
    // An overflow with OF already 1 leaves OF set and does not request LCOFI. The counter can wrap in any mode.
    cp_of_already_set:         cross mhpmevent_of_was_one, mhpmevent_of_one, mhpmcounter_wraps, lcofi_ip_zero;
    cp_overflow_hw_only:       cross priv_mode_m, mip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
    cp_lcofip_hw_only:         cross priv_mode_m, mhpmevent_of, lcofi_ip_zero;
    cp_scountovf_mcounteren:   cross priv_mode_m, scountovf_read, of_write_pattern, mcounteren_stimulus_pattern_state;
    cp_scountovf_shadow:       cross priv_mode_m, scountovf_read, mcounteren_all_ones_state, of_stimulus_pattern;
    cp_sscofpmf_access:        cross priv_mode_m, csr_access_pattern, hpm_csr_target_m;
    cp_lcofi_m:                cross priv_mode_m, lcofi_ip, lcofi_ie, lcofi_mideleg, mstatus_mie_set;
    cp_lcofip_priority_m:      cross priv_mode_m, mhpmevent_inhibits_zero_state, mstatus_mie_set, mie_state, lcofi_ip_one, mip_other_pending;
endgroup
`endif

covergroup Sscofpmf_S_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sscofpmf.svh"

    sip_lcofi: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sip", "lcofip")[0] {}
    sip_lcofi_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sip", "lcofip")[0] {
            bins one = {1};
    }
    sip_lcofi_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sip", "lcofip")[0] {
            bins zero = {0};
    }
    // S-mode clears LCOFIP through sip, so check sip rather than mip here.
    sip_clear: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sip", "sip") == 0) {
            bins yes = {1};
    }

    sie_lcofi: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sie", "lcofie")[0] {}
    sstatus_sie_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstatus", "sie")[0] {
            bins one = {1};
    }

    prev_mstatus_sie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0] {
            bins one = {1};
    }
    sie_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sie", "sie")[15:0]) {
            bins all_zeros = {16'b0};
            // sie is WARL; unimplemented bits stay 0 after a write of all-1s, so "all
            // ones" means all ones in the bits this coverpoint actually cares about
            // (LCOFIE + the 3 standard S-mode enables), not a literal all-1s register.
            wildcard bins all_ones = {16'b??1???1???1???1?};
    }
    lcofi_ip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "lcofip")[0] {
            bins one  = {1};
    }
    mip_other_pending_s: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "seip")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "stip")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "ssip")[0]} {
            bins none = {3'b000};
            `ifdef UDB_SEI_INTR_IMPL
            bins seip = {3'b100};
            `endif
            `ifdef UDB_STI_INTR_IMPL
            bins stip = {3'b010};
            `endif
            `ifdef UDB_SSI_INTR_IMPL
            bins ssip = {3'b001};
            `endif
    }
    mideleg_s_ints: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "lcofip")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "seip")[0],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "stip")[0],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "ssip")[0]} {
            bins delegated = {4'b1111};
    }

    // csrr scountovf (csrrs rd, scountovf, x0)
    scountovf_read: coverpoint ins.current.insn {
        wildcard bins read = {CSRR} iff (ins.current.insn[31:20] == CSR_SCOUNTOVF);
    }

    csr_access_pattern: coverpoint ins.current.insn {
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0);
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1);
        wildcard bins csrrs1    = {CSRRS} iff (ins.current.rs1_val == '1);
        wildcard bins csrrc1    = {CSRRC} iff (ins.current.rs1_val == '1);
        wildcard bins read_only = {CSRRS} iff (ins.current.rs1_val ==  0);
    }

    // M-mode counting stays inhibited so the T-SBI trap handler never counts
    `ifdef UDB_MXLEN_64
        mhpmevent_s_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT, `SSCOFPMF_MHPMEVENT)[62:58]) {
                bins minh_only = {5'b10000};
                bins minh_uinh = {5'b10100};
        }
        mhpmevent_minh_only_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT, `SSCOFPMF_MHPMEVENT)[62:58] == 5'b10000) {
                bins yes = {1};
        }
    `else
        mhpmevent_s_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH, `SSCOFPMF_MHPMEVENTH)[30:26]) {
                bins minh_only = {5'b10000};
                bins minh_uinh = {5'b10100};
        }
        mhpmevent_minh_only_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH, `SSCOFPMF_MHPMEVENTH)[30:26] == 5'b10000) {
                bins yes = {1};
        }
    `endif

    mcounteren_all_ones_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "enable")[28:0] == '1) {
            bins yes = {1};
    }

    mcounteren_stimulus_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "enable")[28:0]) {
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

    lcofi_mideleg_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mideleg", "lcofip")[0] {
            bins one  = {1};
    }

    cp_sinh_inhibits_smode:    cross priv_mode_s, mhpmevent_xinh_combos, mhpmevent_of_zero;
    cp_of_set_on_overflow:     cross priv_mode_s, sip_lcofi_one, mie_clear, mhpmevent_of_one, mhpmevent_s_counts_pattern_state;
    // An overflow with OF already 1 leaves OF set and does not request LCOFI. The counter can wrap in any mode.
    cp_of_already_set:         cross mhpmevent_of_was_one, mhpmevent_of_one, mhpmcounter_wraps, sip_lcofi_zero;
    cp_overflow_hw_only:       cross priv_mode_s, sip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
    cp_lcofip_hw_only:         cross priv_mode_s, mhpmevent_of, sip_lcofi_zero;
    cp_scountovf_shadow:       cross priv_mode_s, scountovf_read, mcounteren_all_ones_state, of_stimulus_pattern;
    cp_scountovf_mcounteren:   cross priv_mode_s, scountovf_read, of_write_pattern, mcounteren_stimulus_pattern_state;
    cp_sscofpmf_access:        cross priv_mode_s, csr_access_pattern, hpm_csr_target;
    cp_lcofi_sip_s:            cross priv_mode_s, sstatus_sie_set, sie_lcofi, sip_lcofi, lcofi_mideleg_one;
    cp_lcofip_priority_s:      cross priv_mode_s, mhpmevent_minh_only_state, prev_mstatus_sie_one, sie_state, lcofi_ip_one, mip_other_pending_s, mideleg_s_ints;
endgroup

covergroup Sscofpmf_U_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sscofpmf.svh"

    `ifdef S_SUPPORTED

        sie_lcofi: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sie", "lcofie")[0] {}
        sip_lcofi: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sip", "lcofip")[0] {}
        sip_lcofi_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sip", "lcofip")[0] {
                bins one = {1};
        }
        sip_lcofi_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sip", "lcofip")[0] {
            bins zero = {0};
        }
        // With S, LCOFIP is cleared through sip, so check sip rather than mip here.
        sip_clear: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sip", "sip") == 0) {
                bins yes = {1};
        }

        sret_insn: coverpoint ins.current.insn {
                type_option.weight = 0;
                bins sret = {SRET};
        }
        old_sstatus_spp_u: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] {
                type_option.weight = 0;
                bins to_u = {0};
        }
    `else
        lcofi_ip_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "lcofip")[0] {
                bins one  = {1};
        }
        lcofi_ip_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "lcofip")[0] {
                bins zero  = {0};
        }

        lcofi_ip: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "lcofip")[0] {}
        lcofi_ie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "lcofie")[0] {}
    `endif

    cp_uinh_inhibits_umode:    cross priv_mode_u, mhpmevent_xinh_combos, mhpmevent_of_zero;
    `ifdef S_SUPPORTED

        // Counting stays inhibited above U so the T-SBI trap handler never counts
        `ifdef UDB_MXLEN_64
            mhpmevent_u_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT, `SSCOFPMF_MHPMEVENT)[62:58]) {
                    bins minh_sinh = {5'b11000};
            }
        `else
            mhpmevent_u_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH, `SSCOFPMF_MHPMEVENTH)[30:26]) {
                    bins minh_sinh = {5'b11000};
            }
        `endif
        cp_of_set_on_overflow: cross priv_mode_u, sip_lcofi_one, mie_clear, mhpmevent_of_one, mhpmevent_u_counts_pattern_state;
    `else
        // Counting stays inhibited above U so the T-SBI trap handler never counts
        `ifdef UDB_MXLEN_64
            mhpmevent_u_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT, `SSCOFPMF_MHPMEVENT)[62:58]) {
                    bins minh_only = {5'b10000};   // SINH is read-only zero without S-mode
            }
        `else
            mhpmevent_u_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH, `SSCOFPMF_MHPMEVENTH)[30:26]) {
                    bins minh_only = {5'b10000};   // SINH is read-only zero without S-mode
            }
        `endif
        cp_of_set_on_overflow: cross priv_mode_u, lcofi_ip_one, mie_clear, mhpmevent_of_one, mhpmevent_u_counts_pattern_state;
    `endif
    // An overflow with OF already 1 leaves OF set and does not request LCOFI. The counter can wrap in any mode.
    `ifdef S_SUPPORTED
        cp_overflow_hw_only:   cross priv_mode_u, sip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
        cp_of_already_set:     cross mhpmevent_of_was_one, mhpmevent_of_one, mhpmcounter_wraps, sip_lcofi_zero;
    `else
        cp_overflow_hw_only:   cross priv_mode_u, mip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
        cp_of_already_set:     cross mhpmevent_of_was_one, mhpmevent_of_one, mhpmcounter_wraps, lcofi_ip_zero;
    `endif
    `ifdef S_SUPPORTED

        cp_lcofip_hw_only:     cross priv_mode_u, mhpmevent_of, sip_lcofi_zero ;

    `else
        cp_lcofip_hw_only:     cross priv_mode_u, mhpmevent_of, lcofi_ip_zero;
    `endif
    `ifdef S_SUPPORTED

        cp_lcofi_sip_u: cross sret_insn, old_sstatus_spp_u, sie_lcofi, sip_lcofi;
    `else

        cp_lcofi_sip_u: cross priv_mode_u, lcofi_ie, lcofi_ip;
    `endif

endgroup

function void sscofpmf_sample(int hart, int issue, ins_t ins);
    `ifndef EXCLUDE_SM
        Sscofpmf_Sm_cg.sample(ins);
    `endif
    Sscofpmf_S_cg.sample(ins);
    Sscofpmf_U_cg.sample(ins);
endfunction
