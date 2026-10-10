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

        // The U-mode tests keep counting inhibited in the modes above U so the T-SBI trap handler
        // never counts. This is the inhibit pattern in which U-mode still counts.
        `ifdef UDB_MXLEN_64
            mhpmevent_u_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[62:58]) {
                    bins minh_sinh = {5'b11000};
            }
        `else
            mhpmevent_u_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[30:26]) {
                    bins minh_sinh = {5'b11000};
            }
        `endif
        cp_of_set_on_overflow: cross priv_mode_u, sip_lcofi_one, mie_clear, mhpmevent_of_one, mhpmevent_u_counts_pattern_state;
    `else
        // The U-mode tests keep counting inhibited in the modes above U so the T-SBI trap handler
        // never counts. This is the inhibit pattern in which U-mode still counts.
        `ifdef UDB_MXLEN_64
            mhpmevent_u_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[62:58]) {
                    bins minh_only = {5'b10000};   // SINH is read-only zero without S-mode
            }
        `else
            mhpmevent_u_counts_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[30:26]) {
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

function void sscofpmfu_sample(int hart, int issue, ins_t ins);
    SscofpmfU_cg.sample(ins);
endfunction
