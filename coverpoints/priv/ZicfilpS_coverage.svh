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

    // ELP before the current instruction: the previous instruction set it
    elp_before: coverpoint (`ZICFILP_LP_BRANCH(ins.prev.insn) &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe")) {
        bins no_lp_expected = {1'b0};
        bins lp_expected    = {1'b1};
    }

    // The current instruction trapped into S-mode (sepc written with its own PC)
    sw_check_exc: coverpoint ins.current.csr[12'h142]
                  iff (ins.current.csr_wb[12'h141] && (ins.current.csr[12'h141] == ins.current.pc_rdata)) {
        bins cause_18 = {18};
    }
    xtval_lpad: coverpoint ins.current.csr[12'h143] {
        `ifdef UDB_REPORT_CAUSE_IN_STVAL_ON_LANDING_PAD_SOFTWARE_CHECK
            bins code_2 = {2};
        `else
            bins zero = {0};
        `endif
    }

    // SPELP after the current instruction (trap entry is logged as an mstatus write)
    spelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "spelp") {
        bins no_lp_expected = {0};
        bins lp_expected    = {1};
    }

    cp_zicfilp_indirect_elp_state_update: cross priv_mode_s, lpe, indirect_ct_prev, rs1_all_prev, lpad_dest;

    `ifdef ZCA_SUPPORTED
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_s, lpe, indirect_ct_prev_c, rs1_all_prev_c, lpad_dest;
    `endif

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_s, lpe_enabled, elp_before, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_s, lpe_enabled, elp_before, lpad_lpl_nonzero, lpl_match {
        ignore_bins ig_mismatch = binsof(lpl_match.mismatch);
    }

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_s, elp_before, not_lpad, sw_check_exc, xtval_lpad {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
    }

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_s, elp_before, lpad_lpl_nonzero, lpl_match, sw_check_exc, xtval_lpad {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
        ignore_bins ig_match = binsof(lpl_match.match);
    }

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_s, elp_before, lpad_scenario {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
    }

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_s, elp_before, sw_check_exc, xtval_lpad, spelp {
        ignore_bins ig_no_lp   = binsof(elp_before.no_lp_expected);
        ignore_bins ig_no_pelp = binsof(spelp.no_lp_expected);
    }

    cp_disabled_zicfilp: cross priv_mode_s, lpe_disabled, indirect_ct_prev, lpad_lpl_nonzero, lpl_match {
        ignore_bins ig_match = binsof(lpl_match.match);
    }

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_s, elp_before, lpad_lpl_zero {
        ignore_bins ig_no_lp = binsof(elp_before.no_lp_expected);
    }

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        instr_access_fault: coverpoint ins.current.csr[12'h142]
                            iff (ins.current.csr_wb[12'h141] && (ins.current.csr[12'h141] == `RVMODEL_ACCESS_FAULT_ADDRESS)) {
            bins cause_1 = {1};
        }
        cp_exception_priority_zicfilp: cross priv_mode_s, lpe_enabled, lp_jalr_to_fault_addr, instr_access_fault, spelp {
            ignore_bins ig_no_pelp = binsof(spelp.no_lp_expected);
        }
    `endif

    // S-mode trap entry and return

    ebreak: coverpoint ins.current.insn {
        bins ebreak = {EBREAK};
    }
    sret: coverpoint ins.current.insn {
        bins sret = {SRET};
    }

    // The current instruction trapped into S-mode (sepc written with its own PC)
    s_trap_here: coverpoint (ins.current.csr_wb[12'h141] && (ins.current.csr[12'h141] == ins.current.pc_rdata)) {
        bins trap = {1'b1};
    }

    // ELP before the current instruction in U-mode, which uses senvcfg.LPE
    elp_before_u: coverpoint (`ZICFILP_LP_BRANCH(ins.prev.insn) &&
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "senvcfg", "lpe")) {
        bins no_lp_expected = {1'b0};
        bins lp_expected    = {1'b1};
    }

    // Trap from S-mode into S-mode saves ELP in SPELP
    cp_pelp_trap_entry_s_zicfilp: cross priv_mode_s, s_trap_here, elp_before, spelp {
        ignore_bins ig_nolp_lp = binsof(elp_before.no_lp_expected) && binsof(spelp.lp_expected);
        ignore_bins ig_lp_nolp = binsof(elp_before.lp_expected)    && binsof(spelp.no_lp_expected);
    }

    // A software-guarded branch (rs1 = x1/x5/x7) with menvcfg.LPE=1 leaves ELP clear, so a trap at its target saves SPELP=0
    cp_pelp_trap_entry_s_guarded_zicfilp: cross priv_mode_s, lpe_enabled, indirect_ct_prev, rs1_link_prev, ebreak, s_trap_here, spelp {
        ignore_bins ig_pelp = binsof(spelp.lp_expected);
    }
    `ifdef ZCA_SUPPORTED
        cp_pelp_trap_entry_s_guarded_zicfilp_c: cross priv_mode_s, lpe_enabled, indirect_ct_prev_c, rs1_link_prev_c, ebreak, s_trap_here, spelp {
            ignore_bins ig_pelp = binsof(spelp.lp_expected);
        }
    `endif

    // Trap from U-mode into S-mode saves ELP in SPELP
    `ifdef U_SUPPORTED
        cp_elp_state_preservation_s_zicfilp: cross priv_mode_u, s_trap_here, elp_before_u, spelp {
            ignore_bins ig_nolp_lp = binsof(elp_before_u.no_lp_expected) && binsof(spelp.lp_expected);
            ignore_bins ig_lp_nolp = binsof(elp_before_u.lp_expected)    && binsof(spelp.no_lp_expected);
        }
    `endif

    // SRET sets ELP from SPELP only if xLPE of the mode it returns to is 1, and clears SPELP
    sret_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "sstatus", "spp") {
        bins S_mode = {1'b1};
        `ifdef U_SUPPORTED
            bins U_mode = {1'b0};
        `endif
    }
    sret_lpe: coverpoint (
        (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "sstatus", "spp") == 1'b1) ?
            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe") :
            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "senvcfg", "lpe")
        ) {
        bins disabled = {0};
        bins enabled  = {1};
    }
    // SPELP written through the sstatus view, which is how the test sets it up before SRET
    spelp_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "sstatus", "spelp") {
        bins no_lp_expected = {0};
        bins lp_expected    = {1};
    }
    cp_pelp_trap_return_s_zicfilp: cross priv_mode_s, sret, sret_mode, sret_lpe, spelp_before, spelp {
        ignore_bins ig_pelp = binsof(spelp.lp_expected);
    }

endgroup

function void zicfilps_sample(int hart, int issue, ins_t ins);
    ZicfilpS_cg.sample(ins);
endfunction
