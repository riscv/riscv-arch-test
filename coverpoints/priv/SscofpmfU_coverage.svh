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

`define COVER_SSCOFPMFU

covergroup SscofpmfU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_sscofpmf.svh"

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

        // The workload runs in U-mode, so with U-mode counting inhibited it cannot overflow the counter
        // (only a hart counting the T-SBI round trip in S/M-mode could, and the test must not rely on that).
        cp_of_set_on_overflow: cross priv_mode_u, sip_lcofi_one, mie_clear, mhpmevent_of_one, mhpmevent_inhibits_pattern_state {
            ignore_bins self_inhibited = binsof(mhpmevent_inhibits_pattern_state.uinh_only) ||
                                         binsof(mhpmevent_inhibits_pattern_state.msu_set);
        }
    `else
        // The workload runs in U-mode, so with U-mode counting inhibited it cannot overflow the counter
        // (only a hart counting the T-SBI round trip in S/M-mode could, and the test must not rely on that).
        cp_of_set_on_overflow: cross priv_mode_u, lcofi_ip_one, mie_clear, mhpmevent_of_one, mhpmevent_inhibits_pattern_state {
            ignore_bins self_inhibited = binsof(mhpmevent_inhibits_pattern_state.uinh_only) ||
                                         binsof(mhpmevent_inhibits_pattern_state.msu_set);
        }
    `endif
    `ifdef S_SUPPORTED
        // Armed with OF already 1: counter at all ones, counting enabled, LCOFIP clear. Only the
        // OF-already-set test reaches this state; its signature checks that the overflow leaves
        // OF set and raises no LCOFI request (norm:count_overflow_interrupt).
        cp_of_already_set_overflow: cross priv_mode_u, sip_lcofi_zero, mie_clear, mhpmevent_of_one, mhpmevent_inhibits_pattern_state, mhpmcounter_extreme_state {
            ignore_bins counting_inhibited = binsof(mhpmevent_inhibits_pattern_state.msu_set) ||
                                             binsof(mhpmevent_inhibits_pattern_state.minh_only) ||
                                             binsof(mhpmevent_inhibits_pattern_state.sinh_only) ||
                                             binsof(mhpmevent_inhibits_pattern_state.uinh_only);
            ignore_bins counter_zero = binsof(mhpmcounter_extreme_state.all_zeros);
        }
    `else
        cp_of_already_set_overflow: cross priv_mode_u, lcofi_ip_zero, mie_clear, mhpmevent_of_one, mhpmevent_inhibits_pattern_state, mhpmcounter_extreme_state {
            ignore_bins counting_inhibited = binsof(mhpmevent_inhibits_pattern_state.msu_set) ||
                                             binsof(mhpmevent_inhibits_pattern_state.minh_only) ||
                                             binsof(mhpmevent_inhibits_pattern_state.sinh_only) ||
                                             binsof(mhpmevent_inhibits_pattern_state.uinh_only);
            ignore_bins counter_zero = binsof(mhpmcounter_extreme_state.all_zeros);
        }
    `endif
    `ifdef S_SUPPORTED
        cp_overflow_hw_only:   cross priv_mode_u, sip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
    `else
        cp_overflow_hw_only:   cross priv_mode_u, mip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
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

function void sscofpmfu_sample(int hart, int issue, ins_t ins);
    SscofpmfU_cg.sample(ins);
endfunction
