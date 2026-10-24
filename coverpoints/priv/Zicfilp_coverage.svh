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

`define COVER_ZICFILP

// Sm tests are not part of a certificate without Sm (EXCLUDE_SM), so neither is their covergroup
`ifndef EXCLUDE_SM
covergroup Zicfilp_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfilp_coverpoints.svh"

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
    sw_check_exc: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code")
                  iff (ins.current.csr_wb[CSR_MEPC] &&
                       (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mepc", "mepc") == ins.current.pc_rdata)) {
        bins software_check = {SOFTWARE_CHECK};
    }
    xtval_lpad: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtval", "mtval") {
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
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_m, lpe, indirect_ct_prev_c, rs1_all_prev, lpad_dest;
    `endif

    // Direct jumps and taken branches are not Indirect_CTs: ELP stays clear at a non-LPAD target
    cp_zicfilp_direct_ct_no_elp: cross priv_mode_m, lpe_enabled, direct_ct_prev, not_lpad;

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_valid, x7_low_bits;

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_m, lpe_enabled, lp_branch_prev, not_lpad;

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_mismatch_only, x7_label_nonzero, x7_low_bits;

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_scenario;

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_mismatch_only,
                                                    x7_label_nonzero, sw_check_exc, xtval_lpad, mpelp;

    cp_disabled_zicfilp: cross priv_mode_m, lpe_disabled, lp_branch_prev, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match_only, pc_aligned;

    cp_exception_priority_zicfilp: cross priv_mode_m, lpe_enabled, priority_case;

    cp_lpad_nop_no_lp_expected_zicfilp: cross priv_mode_m, lpe_enabled, no_lp_branch_prev, lpad_nop_case;

    `ifdef ZCA_SUPPORTED
        cp_lpad_alignment_exception_zicfilp: cross priv_mode_m, lpe_enabled, lp_branch_prev, lpad_lpl_zero, pc_misaligned;
    `endif

    // M-mode trap entry and return

    illegal: coverpoint ins.current.insn {
        bins zeros = {32'h00000000};
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
    elp_before: coverpoint (`ZICFILP_LP_BRANCH(ins.prev) &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mseccfg", "mlpe")) {
        bins no_lp_expected = {1'b0};
    }

    // An illegal instruction in M-mode with ELP=NO_LP_EXPECTED traps into M-mode and saves MPELP=0
    cp_pelp_trap_entry_zicfilp: cross priv_mode_m, lpe_enabled, elp_before, illegal;

    // A software-guarded branch (rs1 = x1/x5/x7) with MLPE=1 leaves ELP clear, so an illegal instruction at its target
    // saves MPELP=0
    cp_pelp_trap_entry_guarded_zicfilp: cross priv_mode_m, lpe_enabled, indirect_ct_prev, rs1_link_prev, illegal;
    `ifdef ZCA_SUPPORTED
        cp_pelp_trap_entry_guarded_zicfilp_c:
            cross priv_mode_m, lpe_enabled, indirect_ct_prev_c, rs1_link_prev, illegal;
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
        cp_pelp_trap_return_zicfilp: cross priv_mode_m_s_u, mret_prev, mseccfg_mlpe, menvcfg_lpe, senvcfg_lpe,
                                             mpelp_before_mret, not_lpad;
    `elsif U_SUPPORTED
        cp_pelp_trap_return_zicfilp: cross priv_mode_m_u, mret_prev, mseccfg_mlpe, menvcfg_lpe, mpelp_before_mret, not_lpad;
    `else
        cp_pelp_trap_return_zicfilp: cross priv_mode_m, mret_prev, mseccfg_mlpe, mpelp_before_mret, not_lpad;
    `endif

    // An S-mode software interrupt pending, enabled and not delegated at an MRET to S-mode with MPELP=1 and
    // menvcfg.LPE=1: the interrupt is taken right after the MRET, before its target, and must save MPELP=1
    `ifdef S_SUPPORTED
        mret_current: coverpoint ins.current.insn {
            bins mret = {MRET};
        }
        mpp_s: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0] {
            bins s_mode = {2'b01};
        }
        `ifdef UDB_MXLEN_32
            mpelp_set_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpelp") {
                bins lp_expected = {1};
            }
        `else
            mpelp_set_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpelp") {
                bins lp_expected = {1};
            }
        `endif
        menvcfg_lpe_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "lpe") {
            bins enabled = {1};
        }
        // {mip.SSIP, mie.SSIE, mideleg.SSI}
        ssi_pending_undelegated: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "ssip")[0],
                                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "ssie")[0],
                                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mideleg", "ssip")[0]} {
            bins pending = {3'b110};
        }
        cp_elp_async_interrupt_zicfilp: cross priv_mode_m, mret_current, mpp_s, mpelp_set_before, menvcfg_lpe_enabled,
                                              ssi_pending_undelegated;
    `endif

endgroup
`endif

covergroup Zicfilp_S_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfilp_coverpoints.svh"

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
    sw_check_exc: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code")
                  iff (ins.current.csr_wb[CSR_SEPC] &&
                      (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sepc", "sepc") == ins.current.pc_rdata)) {
        bins software_check = {SOFTWARE_CHECK};
    }
    xtval_lpad: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval") {
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
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_s, lpe, indirect_ct_prev_c, rs1_all_prev, lpad_dest;
    `endif

    // Direct jumps and taken branches are not Indirect_CTs: ELP stays clear at a non-LPAD target
    cp_zicfilp_direct_ct_no_elp: cross priv_mode_s, lpe_enabled, direct_ct_prev, not_lpad;

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_valid, x7_low_bits;

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_s, lpe_enabled, lp_branch_prev, not_lpad;

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_mismatch_only, x7_label_nonzero, x7_low_bits;

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_scenario;

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_mismatch_only,
                                                    x7_label_nonzero, sw_check_exc, xtval_lpad, spelp;

    cp_disabled_zicfilp: cross priv_mode_s, lpe_disabled, lp_branch_prev, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match_only, pc_aligned;

    cp_exception_priority_zicfilp: cross priv_mode_s, lpe_enabled, priority_case;

    cp_lpad_nop_no_lp_expected_zicfilp: cross priv_mode_s, lpe_enabled, no_lp_branch_prev, lpad_nop_case;

    `ifdef ZCA_SUPPORTED
        cp_lpad_alignment_exception_zicfilp: cross priv_mode_s, lpe_enabled, lp_branch_prev, lpad_lpl_zero, pc_misaligned;
    `endif

    // S-mode trap entry and return

    illegal: coverpoint ins.current.insn {
        bins zeros = {32'h00000000};
    }

    // ELP before the current instruction: the previous instruction set it
    elp_before: coverpoint (`ZICFILP_LP_BRANCH(ins.prev) &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe")) {
        bins no_lp_expected = {1'b0};
    }

    // An illegal instruction in S-mode with ELP=NO_LP_EXPECTED traps into S-mode and saves SPELP=0
    cp_pelp_trap_entry_zicfilp: cross priv_mode_s, lpe_enabled, elp_before, illegal;

    // A software-guarded branch (rs1 = x1/x5/x7) with menvcfg.LPE=1 leaves ELP clear, so an illegal instruction
    // at its target saves SPELP=0
    cp_pelp_trap_entry_guarded_zicfilp: cross priv_mode_s, lpe_enabled, indirect_ct_prev, rs1_link_prev, illegal;
    `ifdef ZCA_SUPPORTED
        cp_pelp_trap_entry_guarded_zicfilp_c:
            cross priv_mode_s, lpe_enabled, indirect_ct_prev_c, rs1_link_prev, illegal;
    `endif

    // A trap from U-mode into S-mode, at the non-LPAD target of an ELP-setting Indirect_CT or at an ecall
    u_lpe_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe") {
        bins enabled = {1};
    }
    cp_elp_state_preservation_zicfilp: cross priv_mode_u, u_lpe_enabled, trap_case;

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
    cp_pelp_trap_return_zicfilp: cross priv_mode_s_u, sret_prev, menvcfg_lpe, senvcfg_lpe, spelp_before_sret, not_lpad;

endgroup

covergroup Zicfilp_U_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfilp_coverpoints.svh"

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
        sw_check_exc: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code")
                      iff (ins.current.csr_wb[CSR_SEPC] &&
                           (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sepc", "sepc") == ins.current.pc_rdata)) {
            bins software_check = {SOFTWARE_CHECK};
        }
        xtval_lpad: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval") {
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
        sw_check_exc: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code")
                      iff (ins.current.csr_wb[CSR_MEPC] &&
                           (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mepc", "mepc") == ins.current.pc_rdata)) {
            bins software_check = {SOFTWARE_CHECK};
        }
        xtval_lpad: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtval", "mtval") {
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
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_u, lpe, indirect_ct_prev_c, rs1_all_prev, lpad_dest;
    `endif

    // Direct jumps and taken branches are not Indirect_CTs: ELP stays clear at a non-LPAD target
    cp_zicfilp_direct_ct_no_elp: cross priv_mode_u, lpe_enabled, direct_ct_prev, not_lpad;

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_valid, x7_low_bits;

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_u, lpe_enabled, lp_branch_prev, not_lpad;

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_mismatch_only, x7_label_nonzero, x7_low_bits;

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_scenario;

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_mismatch_only,
                                                    x7_label_nonzero, sw_check_exc, xtval_lpad, xpelp;

    cp_disabled_zicfilp: cross priv_mode_u, lpe_disabled, lp_branch_prev, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match_only, pc_aligned;

    cp_exception_priority_zicfilp: cross priv_mode_u, lpe_enabled, priority_case;

    cp_lpad_nop_no_lp_expected_zicfilp: cross priv_mode_u, lpe_enabled, no_lp_branch_prev, lpad_nop_case;

    `ifdef ZCA_SUPPORTED
        cp_lpad_alignment_exception_zicfilp: cross priv_mode_u, lpe_enabled, lp_branch_prev, lpad_lpl_zero, pc_misaligned;
    `endif

endgroup

function void zicfilp_sample(int hart, int issue, ins_t ins);
    `ifndef EXCLUDE_SM
        Zicfilp_Sm_cg.sample(ins);
    `endif
    Zicfilp_S_cg.sample(ins);
    Zicfilp_U_cg.sample(ins);
endfunction
