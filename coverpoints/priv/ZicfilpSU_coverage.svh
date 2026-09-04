///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Eman   email:fatehulnasareman@gmail.com (UET, May 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Zicfilp U-mode Coverage (S-mode Implemented)
//
///////////////////////////////////////////////

`define COVER_ZICFILPSU

covergroup Zicfilpsu_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "Zicfilp_coverpoints.svh"

    spelp: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "sstatus", "spelp") {
        bins lp_expected    = {1};
        bins no_lp_expected = {0};
    }
    menvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "menvcfg", "lpe") {
        bins enabled  = {1};
        bins disabled = {0};
    }
    lpe_disabled: coverpoint get_csr_val(ins.hart, ins.issue,
                                `SAMPLE_CURRENT, "menvcfg", "lpe") {
        bins disabled = {0};
    }
    xtval_lpad: coverpoint ins.current.csr[12'h343] {
        bins code_2 = {2};
    }
    cp_zicfilp_indirect_elp_state_update: cross priv_mode_u, menvcfg_lpe, indirect_ct_prev, rs1_all_prev, lpad_dest, spelp;

    `ifdef COVER_ZCA
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_u, menvcfg_lpe, indirect_ct_prev_c, rs1_all_prev_c, lpad_dest, spelp;
    `endif
    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_u, spelp, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_u, spelp, lpad_lpl_nonzero, lpl_match {
        ignore_bins ig_mismatch = binsof(lpl_match.mismatch);
    }

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_u, spelp, not_lpad, sw_check_exc, xtval_lpad {
        ignore_bins ig_no_lp = binsof(spelp.no_lp_expected);
    }

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_u, spelp, lpad_lpl_nonzero, lpl_match, sw_check_exc, xtval_lpad {
        ignore_bins ig_no_lp = binsof(spelp.no_lp_expected);
        ignore_bins ig_match = binsof(lpl_match.match);
    }

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_u, spelp, lpad_scenario {
        ignore_bins ig_no_lp = binsof(spelp.no_lp_expected);
    }

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_u, spelp, sw_check_exc, xtval_lpad {
        ignore_bins ig_no_lp = binsof(spelp.no_lp_expected);
    }

    cp_disabled_zicfilp: cross priv_mode_u, lpe_disabled, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_u, lpad_lpl_zero, spelp {
        ignore_bins ig_no_lp = binsof(spelp.no_lp_expected);
    }

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        cp_exception_priority_zicfilp: cross priv_mode_u, spelp, pc_fault_addr {
            ignore_bins ig_no_lp = binsof(spelp.no_lp_expected);
        }
    `endif
endgroup

function void zicfilpus_sample(int hart, int issue, ins_t ins);
    Zicfilpsu_cg.sample(ins);
endfunction
