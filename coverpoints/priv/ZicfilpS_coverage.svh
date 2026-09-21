///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Eman Nasar  email:fatehulnasareman@gmail.com (UET, May 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Zicfilp S-mode Coverage
//
// xLPE is menvcfg.LPE. Software-check exceptions from S-mode are delegated to S-mode.
///////////////////////////////////////////////

`define COVER_ZICFILPS

covergroup ZicfilpS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "Zicfilp_coverpoints.svh"

    // S-mode landing pad enable
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
    spelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "spelp") {
        bins lp_expected = {1};
    }

    cp_zicfilp_indirect_elp_state_update: cross priv_mode_s, lpe, indirect_ct_prev, rs1_all_prev, lpad_dest;

    `ifdef ZCA_SUPPORTED
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_s, lpe, indirect_ct_prev_c, rs1_all_prev_c, lpad_dest;
    `endif

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_valid;

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_s, lpe_enabled, lp_branch_prev, not_lpad;

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match, x7_label {
        ignore_bins ig_match   = binsof(lpl_match.match);
        ignore_bins ig_x7_zero = binsof(x7_label.label_zero);
    }

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_scenario;

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match,
                                                    x7_label, sw_check_exc, xtval_lpad, spelp {
        ignore_bins ig_match   = binsof(lpl_match.match);
        ignore_bins ig_x7_zero = binsof(x7_label.label_zero);
    }

    cp_disabled_zicfilp: cross priv_mode_s, lpe_disabled, lp_branch_prev, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match, pc_aligned {
        ignore_bins ig_mismatch = binsof(lpl_match.mismatch);
    }

    cp_exception_priority_zicfilp: cross priv_mode_s, lpe_enabled, priority_case;

    `ifdef ZCA_SUPPORTED
        cp_lpad_alignment_exception_zicfilp: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_zero, pc_misaligned;
    `endif

    // S-mode trap entry and return

    ebreak: coverpoint ins.current.insn {
        bins ebreak = {EBREAK};
    }

    // ELP before the current instruction: the previous instruction set it
    elp_before: coverpoint (`ZICFILP_LP_BRANCH(ins.prev.insn) &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe")) {
        bins no_lp_expected = {1'b0};
    }

    // An EBREAK in S-mode with ELP=NO_LP_EXPECTED traps into S-mode and saves SPELP=0
    cp_pelp_trap_entry_s_zicfilp: cross priv_mode_s, lpe_enabled, elp_before, ebreak;

    // A software-guarded branch (rs1 = x1/x5/x7) with menvcfg.LPE=1 leaves ELP clear, so an EBREAK at its target
    // saves SPELP=0
    cp_pelp_trap_entry_s_guarded_zicfilp: cross priv_mode_s, lpe_enabled, indirect_ct_prev, rs1_link_prev, ebreak;
    `ifdef ZCA_SUPPORTED
        cp_pelp_trap_entry_s_guarded_zicfilp_c: cross priv_mode_s, lpe_enabled, indirect_ct_prev_c, rs1_link_prev_c, ebreak;
    `endif

    // A trap from U-mode into S-mode, at the non-LPAD target of an ELP-setting Indirect_CT or at an ecall
    u_lpe_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe") {
        bins enabled = {1};
    }
    cp_elp_state_preservation_s_zicfilp: cross priv_mode_u, u_lpe_enabled, trap_case;

    // SRET to a non-LPAD instruction, sampled at that instruction:
    // mode returned to x menvcfg.LPE x senvcfg.LPE x SPELP before the SRET
    sret_prev: coverpoint ins.prev.insn {
        bins sret = {SRET};
    }
    menvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    senvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    // SPELP before the SRET, two records back (the test's T-SBI call refreshes the mstatus log after it writes SPELP)
    spelp_before_sret: coverpoint get_csr_val(ins.hart, ins.issue, 2, "mstatus", "spelp") {
        bins no_lp_expected = {0};
        bins lp_expected    = {1};
    }
    cp_pelp_trap_return_s_zicfilp: cross priv_mode_s_u, sret_prev, menvcfg_lpe, senvcfg_lpe, spelp_before_sret, not_lpad;

endgroup

function void zicfilps_sample(int hart, int issue, ins_t ins);
    ZicfilpS_cg.sample(ins);
endfunction
