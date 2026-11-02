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

// An indirect call/jump sets ELP=LP_EXPECTED (when xLPE=1) unless rs1 is x1, x5, or x7.
// TD is a trace record (ins.prev or ins.current). ZICFILP_RS1 is its decoded rs1 for jalr, c.jr and c.jalr,
// and x0 for any other instruction. c.ebreak shares the c.jalr encoding with rs1=x0 and has no rs1 operand.
`define ZICFILP_INDIRECT(TD)   ((TD.insn ==? JALR) || (TD.insn ==? C_JR) || (TD.insn ==? C_JALR))
`define ZICFILP_RS1(TD)        gpr_name_t'((`ZICFILP_INDIRECT(TD) && TD.has_rs1) ? ins.get_gpr_reg(TD.rs1) : x0)
`define ZICFILP_RS1_LINK(TD)   ((`ZICFILP_RS1(TD) == x1) || (`ZICFILP_RS1(TD) == x5) || (`ZICFILP_RS1(TD) == x7))
`define ZICFILP_LP_JALR(TD)    ((TD.insn ==? JALR) && !`ZICFILP_RS1_LINK(TD))
`define ZICFILP_LP_CJUMP(TD)   (((TD.insn ==? C_JR) || (TD.insn ==? C_JALR)) && (`ZICFILP_RS1(TD) != x0) && !`ZICFILP_RS1_LINK(TD))
`ifdef ZCA_SUPPORTED
    `define ZICFILP_LP_BRANCH(TD) (`ZICFILP_LP_JALR(TD) || `ZICFILP_LP_CJUMP(TD))
`else
    `define ZICFILP_LP_BRANCH(TD) `ZICFILP_LP_JALR(TD)
`endif

// Sm tests are not part of a certificate without Sm (EXCLUDE_SM), so neither is their covergroup
`ifndef EXCLUDE_SM
covergroup Zicfilp_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfilp_coverpoints.svh"

    // M-mode landing pad enable
    lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mseccfg", "mlpe")[0] {}
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
                            (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mseccfg", "mlpe") == 1)) {
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
    mseccfg_mlpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mseccfg", "mlpe")[0] {}
    menvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe")[0] {}
    // MPELP before the MRET, two records back
    `ifdef UDB_MXLEN_32
        mpelp_before_mret: coverpoint get_csr_val(ins.hart, ins.issue, 2, "mstatush", "mpelp")[0] {}
    `else
        mpelp_before_mret: coverpoint get_csr_val(ins.hart, ins.issue, 2, "mstatus", "mpelp")[0] {}
    `endif
    `ifdef S_SUPPORTED
        senvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe")[0] {}
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
    lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe")[0] {}
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
                            (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "menvcfg", "lpe") == 1)) {
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
    menvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe")[0] {}
    senvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe")[0] {}
    // SPELP before the SRET, two records back (the test's T-SBI call refreshes the mstatus log after it writes SPELP)
    spelp_before_sret: coverpoint get_csr_val(ins.hart, ins.issue, 2, "mstatus", "spelp")[0] {}
    cp_pelp_trap_return_zicfilp: cross priv_mode_s_u, sret_prev, menvcfg_lpe, senvcfg_lpe, spelp_before_sret, not_lpad;

endgroup

covergroup Zicfilp_U_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfilp_coverpoints.svh"

    `ifdef S_SUPPORTED
        // U-mode landing pad enable
        lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe")[0] {}
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
        lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe")[0] {}
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

// H group: henvcfg.LPE enables landing pads in VS-mode and senvcfg.LPE in VU-mode. hedeleg = 0 unless a test
// delegates, so traps from VS-mode and VU-mode are taken in HS-mode and save ELP in sstatus.SPELP. Traps into
// VS-mode save it in vsstatus.SPELP; an SRET executed in VS-mode restores it from there.
// The tests check the resulting software-check exceptions with their trap count.
`ifdef H_SUPPORTED
covergroup Zicfilp_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfilp_coverpoints.svh"

    // Landing pad enable of the current mode: henvcfg.LPE in VS-mode, senvcfg.LPE in VU-mode
    lpe: coverpoint ((ins.prev.mode == 2'b01) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "henvcfg", "lpe")[0]
                                              : get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe")[0]) {
    }
    lpe_enabled: coverpoint ((ins.prev.mode == 2'b01) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "henvcfg", "lpe")
                                                      : get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe")) {
        bins enabled  = {1};
    }
    lpe_disabled: coverpoint ((ins.prev.mode == 2'b01) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "henvcfg", "lpe")
                                                       : get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe")) {
        bins disabled = {0};
    }

    // The current instruction trapped into HS-mode (sepc written with its own PC)
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
    // sstatus.SPELP after the current instruction (trap entry is logged as an mstatus write)
    spelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "spelp") {
        bins lp_expected = {1};
    }

    // The shared coverpoints, in VS-mode and VU-mode
    cp_zicfilp_indirect_elp_state_update: cross priv_mode_vs_vu, lpe, indirect_ct_prev, rs1_all_prev, lpad_dest;

    `ifdef ZCA_SUPPORTED
        cp_zicfilp_indirect_elp_state_update_c: cross priv_mode_vs_vu, lpe, indirect_ct_prev_c, rs1_all_prev, lpad_dest;
    `endif

    // Direct jumps and taken branches are not Indirect_CTs: ELP stays clear at a non-LPAD target
    cp_zicfilp_direct_ct_no_elp: cross priv_mode_vs_vu, lpe_enabled, direct_ct_prev, not_lpad;

    cp_zicfilp_lpad_zero_label_bypass: cross priv_mode_vs_vu, lpe_enabled, lp_branch_prev, lpad_lpl_zero, x7_label;

    cp_zicfilp_lpad_valid_execution: cross priv_mode_vs_vu, lpe_enabled, lp_branch_prev, lpad_valid, x7_low_bits;

    cp_zicfilp_lpad_missing_instruction_exception: cross priv_mode_vs_vu, lpe_enabled, lp_branch_prev, not_lpad;

    cp_zicfilp_lpad_label_mismatch: cross priv_mode_vs_vu, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_mismatch_only, x7_label_nonzero, x7_low_bits;

    cp_zicfilp_lpad_label_match_mismatch: cross priv_mode_vs_vu, lpe_enabled, lp_branch_prev, lpad_scenario;

    cp_zicfilp_lpad_label_exception_delivery: cross priv_mode_vs_vu, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_mismatch_only,
                                                    x7_label_nonzero, sw_check_exc, xtval_lpad, spelp;

    cp_disabled_zicfilp: cross priv_mode_vs_vu, lpe_disabled, lp_branch_prev, lpad_lpl_nonzero;

    cp_lpad_no_sw_exception_elp_clear_zicfilp: cross priv_mode_vs_vu, lpe_enabled, lp_branch_prev, lpad_lpl_nonzero, lpl_match_only, pc_aligned;

    cp_exception_priority_zicfilp: cross priv_mode_vs_vu, lpe_enabled, priority_case;

    cp_lpad_nop_no_lp_expected_zicfilp: cross priv_mode_vs_vu, lpe_enabled, no_lp_branch_prev, lpad_nop_case;

    `ifdef ZCA_SUPPORTED
        cp_lpad_alignment_exception_zicfilp: cross priv_mode_vs_vu, lpe_enabled, lp_branch_prev, lpad_lpl_zero, pc_misaligned;
    `endif

    illegal: coverpoint ins.current.insn {
        bins zeros = {32'h00000000};
    }

    // ELP before the current instruction: the previous instruction set it
    elp_before: coverpoint (`ZICFILP_LP_BRANCH(ins.prev) &&
                            ((ins.prev.mode == 2'b01) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "henvcfg", "lpe")[0]
                                                      : get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "senvcfg", "lpe")[0])) {
        bins no_lp_expected = {1'b0};
    }

    // An illegal instruction in VS-mode or VU-mode with ELP=NO_LP_EXPECTED traps into HS-mode and saves SPELP=0
    cp_pelp_trap_entry_zicfilp: cross priv_mode_vs_vu, lpe_enabled, elp_before, illegal;

    // A software-guarded branch (rs1 = x1/x5/x7) leaves ELP clear, so an illegal instruction at its target saves SPELP=0
    cp_pelp_trap_entry_guarded_zicfilp: cross priv_mode_vs_vu, lpe_enabled, indirect_ct_prev, rs1_link_prev, illegal;
    `ifdef ZCA_SUPPORTED
        cp_pelp_trap_entry_guarded_zicfilp_c:
            cross priv_mode_vs_vu, lpe_enabled, indirect_ct_prev_c, rs1_link_prev, illegal;
    `endif

    // H-specific coverpoints

    menvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "lpe")[0] {}
    henvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "henvcfg", "lpe")[0] {}
    senvcfg_lpe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "lpe")[0] {}

    // Target of an ELP-setting indirect jump (lp_branch_prev): a non-LPAD instruction, or an LPAD whose nonzero
    // label does not match x7[31:12].
    // Either raises a software-check exception only with landing pads enabled.
    lp_target: coverpoint {(ins.current.insn ==? LPAD),
                           ((ins.current.insn[31:12] != 20'h0) &&
                            (ins.current.insn[31:12] != ins.prev.x_wdata[7][31:12]))} {
        wildcard bins not_lpad      = {2'b0?};
        bins          lpad_mismatch = {2'b11};
    }

    // henvcfg.LPE, not menvcfg.LPE, enables landing pads in VS-mode
    cp_vs_lpe: cross priv_mode_vs, henvcfg_lpe, menvcfg_lpe, lp_branch_prev, lp_target;

    // senvcfg.LPE, not henvcfg.LPE, enables landing pads in VU-mode
    cp_vu_lpe: cross priv_mode_vu, senvcfg_lpe, henvcfg_lpe, lp_branch_prev, lp_target;

    // Trap from VS or VU-mode with ELP = LP_EXPECTED (a non-LPAD target of an ELP-setting jalr)
    // or NO_LP_EXPECTED (an ebreak after anything else), into VS-mode or HS-mode
    trap_elp: coverpoint {(`ZICFILP_LP_JALR(ins.prev) && !(ins.current.insn ==? LPAD)),
                          (!`ZICFILP_LP_BRANCH(ins.prev) && (ins.current.insn == EBREAK))} {
        bins lp_expected    = {2'b10};
        bins no_lp_expected = {2'b01};
    }
    // hedeleg[3] and hedeleg[18] are set together, so bit 18 names the handler for both traps
    trap_to: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[SOFTWARE_CHECK] {}
    mode_lpe_enabled: coverpoint (ins.prev.mode == 2'b01 ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "lpe")
                                                         : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "lpe")) {
        bins enabled = {1};
    }
    cp_trap_entry_spelp: cross priv_mode_vs_vu, mode_lpe_enabled, trap_elp, trap_to;

    // SRET, which the test places before a non-LPAD instruction. It restores ELP from vsstatus.SPELP
    // when executed in VS-mode and from sstatus.SPELP when executed in HS-mode, only if the LPE of the
    // new mode (henvcfg.LPE for VS-mode, senvcfg.LPE for VU-mode) is 1. The test gives the other SPELP
    // the opposite value, so using the wrong one changes the outcome. Each mode writes SPP and SPELP
    // through sstatus, so both crosses read them from the sstatus record; in VS-mode that is vsstatus.
    sret: coverpoint ins.current.insn {
        bins sret = {SRET};
    }
    vs_new_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] {}
    hs_new_mode: coverpoint 2 * get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv") +
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp") {
        bins vu = {2};  // hstatus.SPV = 1, sstatus.SPP = 0
        bins vs = {3};  // hstatus.SPV = 1, sstatus.SPP = 1
    }
    henvcfg_lpe_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "lpe")[0] {}
    senvcfg_lpe_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "lpe")[0] {}
    sstatus_spelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spelp")[0] {}
    // Checked in HS-mode, where vsstatus has its own record
    vsstatus_spelp_differs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "spelp") !=
                                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spelp")) {
        bins differs = {1'b1};
    }
    cp_vs_sret_spelp: cross priv_mode_vs, sret, vs_new_mode, henvcfg_lpe_before, senvcfg_lpe_before, sstatus_spelp;
    cp_hs_sret_spelp: cross priv_mode_hs, sret, hs_new_mode, henvcfg_lpe_before, senvcfg_lpe_before, sstatus_spelp,
                            vsstatus_spelp_differs;

    // sstatus.SPELP written in VS-mode, which is vsstatus.SPELP
    sstatus_spelp_write: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS} iff (ins.current.insn[31:20] == CSR_SSTATUS);
        wildcard bins csrrc = {CSRRC} iff (ins.current.insn[31:20] == CSR_SSTATUS);
    }
    spelp_operand: coverpoint ins.current.rs1_val[23] {
        bins spelp = {1'b1};
    }
    cp_vs_sstatus_spelp: cross priv_mode_vs, sstatus_spelp_write, spelp_operand;

    // SRET from HS-mode to HS-mode (hstatus.SPV = 0) restores ELP from sstatus.SPELP when menvcfg.LPE = 1, and clears
    // sstatus.SPELP, not vsstatus.SPELP, which the test gives the opposite value
    hs_to_hs: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv")[0],
                          get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0]} {
        bins hs = {2'b01};
    }
    menvcfg_lpe_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "lpe")[0] {}
    cp_hs_sret_to_hs_spelp: cross priv_mode_hs, sret, hs_to_hs, menvcfg_lpe_before, sstatus_spelp, vsstatus_spelp_differs;

    // SRET from HS-mode to VS-mode or VU-mode with sstatus.SPELP = 1 and the landing pad enable of the new mode set,
    // while a VS-level software interrupt is pending and enabled, for HS-mode (hideleg.VSSI = 0) or VS-mode
    // (hideleg.VSSI = 1). The interrupt is taken right after the SRET, before its target, and must save SPELP = 1.
    spelp_set_before: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spelp") {
        bins lp_expected = {1};
    }
    new_mode_lpe_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] ?
                                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "lpe")[0] :
                                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "lpe")[0]) {
        bins enabled = {1};
    }
    // {hvip.VSSIP, hie.VSSIE, hideleg.VSSI}
    vssi_pending: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vssip")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip")[0]} {
        bins to_hs = {3'b110};
        bins to_vs = {3'b111};
    }
    cp_elp_async_interrupt: cross priv_mode_hs, sret, hs_new_mode, spelp_set_before, new_mode_lpe_enabled, vssi_pending;

    // A software-check exception delegated to VS-mode (hedeleg[18] = 1) at the target of an ELP-setting indirect jump:
    // vscause, vstval and vsstatus.SPELP = LP_EXPECTED
    vs_sw_check_exc: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vscause", "code")
                     iff (ins.current.csr_wb[CSR_VSCAUSE]) {
        bins software_check = {SOFTWARE_CHECK};
    }
    vstval_lpad: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vstval", "vstval") {
        `ifdef UDB_REPORT_CAUSE_IN_STVAL_ON_LANDING_PAD_SOFTWARE_CHECK
            bins code_2 = {2};
        `else
            bins zero = {0};
        `endif
    }
    vsspelp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vsstatus", "spelp") {
        bins lp_expected = {1};
    }
    cp_vs_trap_delivery: cross priv_mode_vs_vu, mode_lpe_enabled, lp_branch_prev, lp_target, vs_sw_check_exc, vstval_lpad, vsspelp;

endgroup
`endif

// SmH group: the test boots to M-mode with medeleg[3] = medeleg[18] = 0, so breakpoints and software-check
// exceptions from VS-mode and VU-mode are taken in M-mode and save ELP in MPELP. MRET with MPV = 1 restores it.
`ifndef EXCLUDE_SM
`ifdef H_SUPPORTED
covergroup Zicfilp_SmH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    mret : coverpoint ins.current.insn {
        bins mret = {MRET};
    }

    // mret with MPV = 1 to VS-mode or VU-mode sets ELP = MPELP only if the landing pad enable of the new mode
    // (henvcfg.LPE for VS-mode, senvcfg.LPE for VU-mode) is 1
    `ifdef UDB_MXLEN_64
        mret_virt_mode : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv")[0],
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `else
        mret_virt_mode : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv")[0],
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `endif
        bins vu = {3'b100};
        bins vs = {3'b101};
    }
    henvcfg_lpe_before : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "lpe")[0] {}
    senvcfg_lpe_before : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "lpe")[0] {}
    `ifdef UDB_MXLEN_64
        old_mpelp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpelp")[0] {
    `else
        old_mpelp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpelp")[0] {
    `endif
    }
    cp_mret_mpelp_virt: cross priv_mode_m, mret, mret_virt_mode, henvcfg_lpe_before, senvcfg_lpe_before, old_mpelp;

    // A trap from VS-mode or VU-mode into M-mode saves ELP in MPELP: a software-check exception at the non-LPAD
    // target of an ELP-setting jalr (LP_EXPECTED) or an ebreak (NO_LP_EXPECTED)
    virt_lpe_enabled : coverpoint ((ins.prev.mode == 2'b01) ? get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "lpe")
                                                            : get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "lpe")) {
        bins enabled = {1};
    }
    // {software-check exception, ebreak, MPELP after the trap}
    `ifdef UDB_MXLEN_64
        m_trap_elp : coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") == `UDB_MXLEN'(SOFTWARE_CHECK)),
                                 (ins.current.insn == EBREAK),
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mpelp")[0]}
    `else
        m_trap_elp : coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") == `UDB_MXLEN'(SOFTWARE_CHECK)),
                                 (ins.current.insn == EBREAK),
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "mpelp")[0]}
    `endif
                     iff (ins.current.csr_wb[CSR_MCAUSE]) {
        bins lp_expected    = {3'b101};
        bins no_lp_expected = {3'b010};
    }
    cp_trap_mpelp_virt: cross priv_mode_vs_vu, virt_lpe_enabled, m_trap_elp;

    // sstatus.SPELP written in VS-mode is vsstatus.SPELP, for each value of mstatus.SPELP, which must not change
    vs_sstatus_spelp_write : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS} iff (ins.current.insn[31:20] == CSR_SSTATUS);
        wildcard bins csrrc = {CSRRC} iff (ins.current.insn[31:20] == CSR_SSTATUS);
    }
    spelp_operand : coverpoint ins.current.rs1_val[23] {
        bins spelp = {1'b1};
    }
    mstatus_spelp_before : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spelp")[0] {}
    cp_vs_sstatus_spelp_mstatus: cross priv_mode_vs, vs_sstatus_spelp_write, spelp_operand, mstatus_spelp_before;
endgroup
`endif
`endif

function void zicfilp_sample(int hart, int issue, ins_t ins);
    `ifndef EXCLUDE_SM
        Zicfilp_Sm_cg.sample(ins);
    `endif
    Zicfilp_S_cg.sample(ins);
    Zicfilp_U_cg.sample(ins);
    `ifdef H_SUPPORTED
        Zicfilp_H_cg.sample(ins);
        `ifndef EXCLUDE_SM
            Zicfilp_SmH_cg.sample(ins);
        `endif
    `endif
endfunction
