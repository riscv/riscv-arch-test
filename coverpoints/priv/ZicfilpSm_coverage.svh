///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Eman Nasar  email:fatehulnasareman@gmail.com (UET, May 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Zicfilp M-mode Coverage
//
// xLPE is mseccfg.MLPE. Traps from M-mode (and, with medeleg=0, from S/U-mode) are taken in M-mode.
///////////////////////////////////////////////

`define COVER_ZICFILPSM

covergroup ZicfilpSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "Zicfilp_coverpoints.svh"

    // M-mode landing pad enable
    lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mseccfg", "mlpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    lpe_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mseccfg", "mlpe") {
        bins enabled  = {1};
    }
    lpe_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mseccfg", "mlpe") {
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
    // mstatus.MPELP after the current instruction
    `ifdef UDB_MXLEN_32
        mpelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatush", "mpelp") {
            bins lp_expected = {1};
        }
    `else
        mpelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "mpelp") {
            bins lp_expected = {1};
        }
    `endif

    cp_zicfilp_indirect_elp_state_update: cross priv_mode_m, lpe, indirect_ct_prev, rs1_all_prev, lpad_dest;

    `ifdef ZCA_SUPPORTED
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_m, lpe, indirect_ct_prev_c, rs1_all_prev_c, lpad_dest;
    `endif

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_valid;

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_m, lpe_enabled, lp_branch_prev, not_lpad;

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match, x7_label {
        ignore_bins ig_match   = binsof(lpl_match.match);
        ignore_bins ig_x7_zero = binsof(x7_label.label_zero);
    }

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_scenario;

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match,
                                                    x7_label, sw_check_exc, xtval_lpad, mpelp {
        ignore_bins ig_match   = binsof(lpl_match.match);
        ignore_bins ig_x7_zero = binsof(x7_label.label_zero);
    }

    cp_disabled_zicfilp: cross priv_mode_m, lpe_disabled, lp_branch_prev, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match, pc_aligned {
        ignore_bins ig_mismatch = binsof(lpl_match.mismatch);
    }

    cp_exception_priority_zicfilp: cross priv_mode_m, lpe_enabled, priority_case;

    `ifdef ZCA_SUPPORTED
        cp_lpad_alignment_exception_zicfilp: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_zero, pc_misaligned;
    `endif

    // M-mode trap entry and return

    ecall: coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }

    // A trap from S/U-mode into M-mode, at the non-LPAD target of an ELP-setting Indirect_CT or at an ecall,
    // with xLPE=1 in the mode the trap is taken from
    origin_lpe_enabled: coverpoint (
        `ifdef S_SUPPORTED
            (ins.prev.mode == 2'b01) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe") :
                                       get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe")
        `else
            get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe")
        `endif
        ) {
        bins enabled = {1};
    }
    `ifdef S_SUPPORTED
        cp_elp_state_preservation_zicfilp: cross priv_mode_s_u, origin_lpe_enabled, trap_case;
    `elsif U_SUPPORTED
        cp_elp_state_preservation_zicfilp: cross priv_mode_u, origin_lpe_enabled, trap_case;
    `endif

    // ELP before the current instruction: the previous instruction set it
    elp_before: coverpoint (`ZICFILP_LP_BRANCH(ins.prev.insn) &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mseccfg", "mlpe")) {
        bins no_lp_expected = {1'b0};
    }

    // An ECALL in M-mode with ELP=NO_LP_EXPECTED traps into M-mode and saves MPELP=0
    cp_pelp_trap_entry_m_zicfilp: cross priv_mode_m, lpe_enabled, elp_before, ecall;

    // A software-guarded branch (rs1 = x1/x5/x7) with MLPE=1 leaves ELP clear, so an ECALL at its target saves MPELP=0
    cp_pelp_trap_entry_m_guarded_zicfilp: cross priv_mode_m, lpe_enabled, indirect_ct_prev, rs1_link_prev, ecall;
    `ifdef ZCA_SUPPORTED
        cp_pelp_trap_entry_m_guarded_zicfilp_c: cross priv_mode_m, lpe_enabled, indirect_ct_prev_c, rs1_link_prev_c, ecall;
    `endif

    // MRET to a non-LPAD instruction, sampled at that instruction:
    // mode returned to x mseccfg.MLPE x menvcfg.LPE x senvcfg.LPE x MPELP before the MRET
    mret_prev: coverpoint ins.prev.insn {
        bins mret = {MRET};
    }
    mseccfg_mlpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mseccfg", "mlpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    menvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe") {
        bins disabled = {0};
        bins enabled  = {1};
    }
    // MPELP before the MRET, two records back
    `ifdef UDB_MXLEN_32
        mpelp_before_mret: coverpoint get_csr_val(ins.hart, ins.issue, 2, "mstatush", "mpelp") {
            bins no_lp_expected = {0};
            bins lp_expected    = {1};
        }
    `else
        mpelp_before_mret: coverpoint get_csr_val(ins.hart, ins.issue, 2, "mstatus", "mpelp") {
            bins no_lp_expected = {0};
            bins lp_expected    = {1};
        }
    `endif
    `ifdef S_SUPPORTED
        senvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe") {
            bins disabled = {0};
            bins enabled  = {1};
        }
        cp_pelp_trap_return_m_zicfilp: cross priv_mode_m_s_u, mret_prev, mseccfg_mlpe, menvcfg_lpe, senvcfg_lpe,
                                             mpelp_before_mret, not_lpad;
    `elsif U_SUPPORTED
        cp_pelp_trap_return_m_zicfilp: cross priv_mode_m_u, mret_prev, mseccfg_mlpe, menvcfg_lpe, mpelp_before_mret, not_lpad;
    `else
        cp_pelp_trap_return_m_zicfilp: cross priv_mode_m, mret_prev, mseccfg_mlpe, mpelp_before_mret, not_lpad;
    `endif

endgroup

function void zicfilpsm_sample(int hart, int issue, ins_t ins);
    ZicfilpSm_cg.sample(ins);
endfunction
