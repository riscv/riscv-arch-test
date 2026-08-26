///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Eman Nasar  email:fatehulnasareman@gmail.com (UET, May 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Zicfilp Sm-mode Coverage
//
///////////////////////////////////////////////

`define COVER_ZICFILPSM

covergroup Zicfilp_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    `include "Zicfilp_coverpoints.svh"

    `ifdef XLEN64
        elp_before: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "mstatus", "mpelp") {
            bins lp_expected    = {1};
            bins no_lp_expected = {0};
        }
    `else
        elp_before: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "mstatush", "mpelp") {
            bins lp_expected    = {1};
            bins no_lp_expected = {0};
        }
    `endif
    mlpe: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "mseccfg", "mlpe") {
        bins enabled  = {1};
        bins disabled = {0};
    }
    lpe_disabled: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "mseccfg", "mlpe") {
        bins disabled = {0};
    }
    xtval_lpad: coverpoint ins.current.csr[12'h343] {
        bins code_2 = {2};
    }
    `ifdef XLEN64
        mpelp: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "mstatus", "mpelp") {
            bins lp_expected    = {1};
            bins no_lp_expected = {0};
        }
    `else
        mpelp: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "mstatush", "mpelp") {
            bins lp_expected    = {1};
            bins no_lp_expected = {0};
        }
    `endif
    mret: coverpoint ins.current.insn {
        bins mret = {MRET};
    }
    ecall: coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }

    cp_zicfilp_indirect_elp_state_update: cross priv_mode_m, mlpe, indirect_ct_prev, rs1_all_prev, lpad_dest;

    `ifdef COVER_ZCA
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_m, mlpe, indirect_ct_prev_c, rs1_all_prev_c, lpad_dest;
    `endif
    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_m, elp_before, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_m, elp_before, lpad_lpl_nonzero, lpl_match {
        ignore_bins ig_mismatch = binsof(lpl_match.mismatch);
    }

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_m, elp_before, not_lpad, sw_check_exc, xtval_lpad {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
    }

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_m, elp_before, lpad_lpl_nonzero, lpl_match, sw_check_exc, xtval_lpad {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
        ignore_bins ig_match = binsof(lpl_match.match);
    }

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_m, elp_before, lpad_scenario {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
    }

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_m, elp_before, sw_check_exc, xtval_lpad {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
    }

    cp_disabled_zicfilp: cross priv_mode_m, lpe_disabled, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_m, elp_before, lpad_lpl_zero {
        ignore_bins ig_no_lp    = binsof(elp_before.no_lp_expected);
    }

    cp_elp_state_preservation_zicfilp: cross priv_mode_m, ecall, elp_before, mpelp {
        ignore_bins ig_mismatch_nolp_lp = binsof(elp_before.no_lp_expected) && binsof(mpelp.lp_expected);
        ignore_bins ig_mismatch_lp_nolp = binsof(elp_before.lp_expected)    && binsof(mpelp.no_lp_expected);
    }

    cp_pelp_trap_entry_m_zicfilp: cross priv_mode_m, elp_before, mpelp {}

    cp_pelp_trap_entry_m_guarded_zicfilp: cross priv_mode_m, rs1_link, elp_before, mpelp {
        ignore_bins ig_elp_was_lp   = binsof(elp_before.lp_expected);
        ignore_bins ig_mpelp_set    = binsof(mpelp.lp_expected);
    }

    cp_pelp_trap_return_m_zicfilp: cross priv_mode_m, mret, mlpe, mpelp {}

   `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        cp_exception_priority_zicfilp: cross priv_mode_m, elp_before, pc_fault_addr {
            ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
    }
   `endif
endgroup

function void zicfilp_Sm_sample(int hart, int issue, ins_t ins);
    Zicfilp_Sm_cg.sample(ins);
endfunction
