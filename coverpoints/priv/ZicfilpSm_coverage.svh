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

    // ELP before the current instruction: the previous instruction set it
    elp_before: coverpoint (`ZICFILP_LP_BRANCH(ins.prev.insn) &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mseccfg", "mlpe")) {
        bins no_lp_expected = {1'b0};
        bins lp_expected    = {1'b1};
    }

    // The current instruction trapped into M-mode (mepc written with its own PC)
    m_trap_here: coverpoint (ins.current.csr_wb[12'h341] && (ins.current.csr[12'h341] == ins.current.pc_rdata)) {
        bins trap = {1'b1};
    }
    sw_check_exc: coverpoint ins.current.csr[12'h342]
                  iff (ins.current.csr_wb[12'h341] && (ins.current.csr[12'h341] == ins.current.pc_rdata)) {
        bins cause_18 = {18};
    }
    xtval_lpad: coverpoint ins.current.csr[12'h343] {
        `ifdef UDB_REPORT_CAUSE_IN_MTVAL_ON_LANDING_PAD_SOFTWARE_CHECK
            bins code_2 = {2};
        `else
            bins zero = {0};
        `endif
    }

    // mstatus.MPELP after the current instruction
    `ifdef UDB_MXLEN_32
        mpelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatush", "mpelp") {
            bins no_lp_expected = {0};
            bins lp_expected    = {1};
        }
    `else
        mpelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "mpelp") {
            bins no_lp_expected = {0};
            bins lp_expected    = {1};
        }
    `endif

    cp_zicfilp_indirect_elp_state_update: cross priv_mode_m, lpe, indirect_ct_prev, rs1_all_prev, lpad_dest;

    `ifdef ZCA_SUPPORTED
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_m, lpe, indirect_ct_prev_c, rs1_all_prev_c, lpad_dest;
    `endif

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_m, lpe_enabled, elp_before, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_m, lpe_enabled, elp_before, lpad_lpl_nonzero, lpl_match {
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

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_m, elp_before, sw_check_exc, xtval_lpad, mpelp {
        ignore_bins ig_no_lp   = binsof(elp_before.no_lp_expected);
        ignore_bins ig_no_pelp = binsof(mpelp.no_lp_expected);
    }

    cp_disabled_zicfilp: cross priv_mode_m, lpe_disabled, indirect_ct_prev, lpad_lpl_nonzero, lpl_match {
        ignore_bins ig_match = binsof(lpl_match.match);
    }

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_m, elp_before, lpad_lpl_zero {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
    }

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        instr_access_fault: coverpoint ins.current.csr[12'h342]
                            iff (ins.current.csr_wb[12'h341] && (ins.current.csr[12'h341] == `RVMODEL_ACCESS_FAULT_ADDRESS)) {
            bins cause_1 = {1};
        }
        cp_exception_priority_zicfilp: cross priv_mode_m, lpe_enabled, lp_jalr_to_fault_addr, instr_access_fault, mpelp {
            ignore_bins ig_no_pelp = binsof(mpelp.no_lp_expected);
        }
    `endif

    // M-mode trap entry and return

    ecall: coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    mret: coverpoint ins.current.insn {
        bins mret = {MRET};
    }

    // ELP before the current instruction in S/U-mode, using that mode's xLPE
    elp_before_su: coverpoint (`ZICFILP_LP_BRANCH(ins.prev.insn) && (
        `ifdef S_SUPPORTED
            (ins.prev.mode == 2'b01) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe") :
                                       get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "senvcfg", "lpe")
        `else
            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe")
        `endif
        )) {
        bins no_lp_expected = {1'b0};
        bins lp_expected    = {1'b1};
    }

    // Trap from S/U-mode into M-mode saves ELP in MPELP
    `ifdef S_SUPPORTED
        cp_elp_state_preservation_zicfilp: cross priv_mode_s_u, m_trap_here, elp_before_su, mpelp {
            ignore_bins ig_nolp_lp = binsof(elp_before_su.no_lp_expected) && binsof(mpelp.lp_expected);
            ignore_bins ig_lp_nolp = binsof(elp_before_su.lp_expected)    && binsof(mpelp.no_lp_expected);
        }
    `elsif U_SUPPORTED
        cp_elp_state_preservation_zicfilp: cross priv_mode_u, m_trap_here, elp_before_su, mpelp {
            ignore_bins ig_nolp_lp = binsof(elp_before_su.no_lp_expected) && binsof(mpelp.lp_expected);
            ignore_bins ig_lp_nolp = binsof(elp_before_su.lp_expected)    && binsof(mpelp.no_lp_expected);
        }
    `endif

    // Trap from M-mode into M-mode saves ELP in MPELP
    cp_pelp_trap_entry_m_zicfilp: cross priv_mode_m, m_trap_here, elp_before, mpelp {
        ignore_bins ig_nolp_lp = binsof(elp_before.no_lp_expected) && binsof(mpelp.lp_expected);
        ignore_bins ig_lp_nolp = binsof(elp_before.lp_expected)    && binsof(mpelp.no_lp_expected);
    }

    // A software-guarded branch (rs1 = x1/x5/x7) with MLPE=1 leaves ELP clear, so a trap at its target saves MPELP=0
    cp_pelp_trap_entry_m_guarded_zicfilp: cross priv_mode_m, lpe_enabled, indirect_ct_prev, rs1_link_prev, ecall, m_trap_here, mpelp {
        ignore_bins ig_pelp = binsof(mpelp.lp_expected);
    }
    `ifdef ZCA_SUPPORTED
        cp_pelp_trap_entry_m_guarded_zicfilp_c: cross priv_mode_m, lpe_enabled, indirect_ct_prev_c, rs1_link_prev_c, ecall, m_trap_here, mpelp {
            ignore_bins ig_pelp = binsof(mpelp.lp_expected);
        }
    `endif

    // MRET sets ELP from MPELP only if xLPE of the mode it returns to is 1, and clears MPELP
    mret_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpp") {
        bins M_mode = {2'b11};
        `ifdef S_SUPPORTED
            bins S_mode = {2'b01};
        `endif
        `ifdef U_SUPPORTED
            bins U_mode = {2'b00};
        `endif
    }
    mret_lpe: coverpoint (
        (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpp") == 2'b11) ?
            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mseccfg", "mlpe") :
        `ifdef S_SUPPORTED
            (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpp") == 2'b01) ?
                get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe") :
                get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "senvcfg", "lpe")
        `else
            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe")
        `endif
        ) {
        bins disabled = {0};
        bins enabled  = {1};
    }
    `ifdef UDB_MXLEN_32
        mpelp_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatush", "mpelp") {
            bins no_lp_expected = {0};
            bins lp_expected    = {1};
        }
    `else
        mpelp_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpelp") {
            bins no_lp_expected = {0};
            bins lp_expected    = {1};
        }
    `endif
    cp_pelp_trap_return_m_zicfilp: cross priv_mode_m, mret, mret_mode, mret_lpe, mpelp_before, mpelp {
        ignore_bins ig_pelp = binsof(mpelp.lp_expected);
    }

endgroup

function void zicfilpsm_sample(int hart, int issue, ins_t ins);
    ZicfilpSm_cg.sample(ins);
endfunction
