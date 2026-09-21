///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Eman Nasar  email:fatehulnasareman@gmail.com (UET, May 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Zicfilp U-mode Coverage
//
// With S-mode, xLPE is senvcfg.LPE and software-check exceptions from U-mode are delegated to S-mode.
// Without S-mode, xLPE is menvcfg.LPE and they are taken in M-mode.
///////////////////////////////////////////////

`define COVER_ZICFILPU

covergroup ZicfilpU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "Zicfilp_coverpoints.svh"

    `ifdef S_SUPPORTED
        // U-mode landing pad enable
        lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe") {
            bins disabled = {0};
            bins enabled  = {1};
        }
        lpe_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe") {
            bins enabled  = {1};
        }
        lpe_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe") {
            bins disabled = {0};
        }

        // The current instruction trapped into S-mode (sepc written with its own PC)
        sw_check_exc: coverpoint ins.current.csr[CSR_SCAUSE]
                      iff (ins.current.csr_wb[CSR_SEPC] && (ins.current.csr[CSR_SEPC] == ins.current.pc_rdata)) {
            bins cause_18 = {18};
        }
        xtval_lpad: coverpoint ins.current.csr[CSR_STVAL] {
            `ifdef UDB_REPORT_CAUSE_IN_STVAL_ON_LANDING_PAD_SOFTWARE_CHECK
                bins code_2 = {2};
            `else
                bins zero = {0};
            `endif
        }
        // SPELP after the current instruction (trap entry is logged as an mstatus write)
        xpelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "spelp") {
            bins lp_expected = {1};
        }
    `else
        // U-mode landing pad enable
        lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe") {
            bins disabled = {0};
            bins enabled  = {1};
        }
        lpe_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe") {
            bins enabled  = {1};
        }
        lpe_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe") {
            bins disabled = {0};
        }

        // The current instruction trapped into M-mode (mepc written with its own PC)
        sw_check_exc: coverpoint ins.current.csr[CSR_MCAUSE]
                      iff (ins.current.csr_wb[CSR_MEPC] && (ins.current.csr[CSR_MEPC] == ins.current.pc_rdata)) {
            bins cause_18 = {18};
        }
        xtval_lpad: coverpoint ins.current.csr[CSR_MTVAL] {
            `ifdef UDB_REPORT_CAUSE_IN_MTVAL_ON_LANDING_PAD_SOFTWARE_CHECK
                bins code_2 = {2};
            `else
                bins zero = {0};
            `endif
        }
        // MPELP after the current instruction
        `ifdef UDB_MXLEN_32
            xpelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatush", "mpelp") {
                bins lp_expected = {1};
            }
        `else
            xpelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "mpelp") {
                bins lp_expected = {1};
            }
        `endif
    `endif

    cp_zicfilp_indirect_elp_state_update: cross priv_mode_u, lpe, indirect_ct_prev, rs1_all_prev, lpad_dest;

    `ifdef ZCA_SUPPORTED
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_u, lpe, indirect_ct_prev_c, rs1_all_prev_c, lpad_dest;
    `endif

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_valid;

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_u, lpe_enabled, lp_branch_prev, not_lpad;

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match, x7_label {
        ignore_bins ig_match   = binsof(lpl_match.match);
        ignore_bins ig_x7_zero = binsof(x7_label.label_zero);
    }

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_scenario;

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match,
                                                    x7_label, sw_check_exc, xtval_lpad, xpelp {
        ignore_bins ig_match   = binsof(lpl_match.match);
        ignore_bins ig_x7_zero = binsof(x7_label.label_zero);
    }

    cp_disabled_zicfilp: cross priv_mode_u, lpe_disabled, lp_branch_prev, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match, pc_aligned {
        ignore_bins ig_mismatch = binsof(lpl_match.mismatch);
    }

    cp_exception_priority_zicfilp: cross priv_mode_u, lpe_enabled, priority_case;

    `ifdef ZCA_SUPPORTED
        cp_lpad_alignment_exception_zicfilp: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_zero, pc_misaligned;
    `endif

endgroup

function void zicfilpu_sample(int hart, int issue, ins_t ins);
    ZicfilpU_cg.sample(ins);
endfunction
