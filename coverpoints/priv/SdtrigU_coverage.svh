///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SDTRIGU
// suite-local defines for the shared coverpoints, undefined at the end of this file
`define SDTRIG_SUITE_U               // the tests run in U-mode
`define SDTRIG_ICOUNT_MODE_BIT 6     // icount tdata1.u: the tests count in U-mode
`define SDTRIG_MCONTROL6_MODE_BIT 3  // mcontrol6 tdata1.u
`include "general/RISCV_coverage_sdtrig_derived.svh"
`include "general/RISCV_coverage_sdtrig_functions.svh"

covergroup SdtrigU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_bp_coverpoints.svh"

    // main coverpoints: breakpoints taken from U-mode
    cp_breakpoint_u: cross priv_mode_u, triggernum, bp_type;  // NTRIG * 2 types; handled in S (medeleg[3] = 1) or M (tcontrol)
    `ifdef S_SUPPORTED
        cp_breakpoint_delegate_u: cross priv_mode_u, triggernum, bp_type, bp_routing;  // NTRIG * 2 types * 2 (medeleg[3] = 0 into M, 1 into S)
    `endif
endgroup

covergroup SdtrigU_access_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_access_coverpoints.svh"

    // main coverpoints
    cp_csr_access_trap_u: cross priv_mode_u, csr_read_write, csr_trigger_mlevel, illegal_insn_trap;  // 2 accesses * implemented M-level trigger CSRs (5-7)
endgroup

covergroup SdtrigU_icount_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_icount_coverpoints.svh"

    // main coverpoints: the readbacks (csrr tdata1) run in M-mode through T-SBI; the fires are taken from U-mode
    `ifdef SDTRIG_ICOUNT_ANY
    `ifdef UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1
        cp_icount_hardwired: cross priv_mode_m, triggernum_icount, csrr, csr_tdata1, icount_readback, armed_hardwired, hardwired_result;  // NTRIG
    `else
        cp_icount_instr:      cross priv_mode_m, triggernum_icount, csrr, csr_tdata1, icount_readback, armed_gt1, icount_count_result;  // NTRIG * 2 u
        cp_icount_instr_fire: cross exec_mode_u, triggernum_icount, icount_fired, fired_gt1_mode;                                         // NTRIG
        cp_icount_eq0:        cross priv_mode_m, triggernum_icount, csrr, csr_tdata1, icount_readback, armed_zero_mode, icount_eq0_result; // NTRIG * 2 pending
        cp_icount_eq0_fire:   cross exec_mode_u, triggernum_icount, icount_fired, fired_zero_pending;                                     // NTRIG
    `endif
    cp_icount_trap:           cross priv_mode_m, triggernum_icount, csrr, csr_tdata1, icount_readback, armed_one, icount_count_result;   // NTRIG * 2 u
    cp_icount_trap_fire:      cross exec_mode_u, triggernum_icount, icount_fired, fired_one_mode;                                          // NTRIG
    `endif
endgroup

covergroup SdtrigU_a_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_a_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    cp_lrsc_addr: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_select_adr, tdata2_rs1, tdata1_xsl_one, lrsc_op, a_outcome;        // NTRIG * 2 tdata2 * 3 xsl * 2 (RV64 4) ops
    cp_lrsc_data: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_select_data, a_tdata2_data, tdata1_xsl_one, lrsc_op_xlen, a_outcome; // NTRIG * 2 tdata2 * 3 xsl * 2 ops
    cp_amo:       cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_select_adr, tdata2_rs1, tdata1_xsl_one, amo_op, a_outcome;         // NTRIG * 2 tdata2 * 3 xsl * 9 (RV64 18) ops
    `endif
endgroup

covergroup SdtrigU_cache_operations_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_cache_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef ZICBOM_SUPPORTED
        cp_cache_zicbom: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, cbo_tdata2, cbo_select, tdata1_size, tdata1_xsl_one, cbom_op, cbo_outcome;                  // NTRIG * 4 tdata2 * 2 select * sizes * 3 xsl * 3 ops
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cp_cache_zicboz: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, cbo_tdata2, cbo_select, tdata1_size, tdata1_xsl_one, cboz_op, cbo_outcome;                  // NTRIG * 4 tdata2 * 2 select * sizes * 3 xsl
    `endif
    `ifdef ZICBOP_SUPPORTED
        cp_cache_zicbop: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata2_rs1, cbo_select, tdata1_size_any, tdata1_xsl_load_store, prefetch_op, cbo_outcome; // NTRIG * 2 tdata2 * 2 select * 3 ops
    `endif
    `endif
endgroup

`ifdef ZVL32B_SUPPORTED
covergroup SdtrigU_combined_accesses_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_vector_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    cp_vector_load_store: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_select_adr, tdata2_rs1, tdata1_size, vec_vl_one, vec_unmasked, vec_access, vec_xsl, vec_outcome;  // NTRIG * 2 tdata2 * sizes * 6 (Zve64x 8) accesses
    cp_vector_accesses:   cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_select_adr, vec_tdata2, tdata1_size_any, vec_vl, vec_unmasked, vec_access, vec_xsl, vec_outcome;    // NTRIG * 3 tdata2 * 2 vl * 6 (8) accesses
    cp_vector_mask:       cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_select_adr, vec_tdata2_plus_8, tdata1_size_any, vec_vl_reaches_8, vec_masked, vec_element_8, vec_access, vec_xsl, vec_outcome; // NTRIG * 2 mask states * 6 (8) accesses
    `endif
endgroup
`endif

covergroup SdtrigU_itrigger_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_trap_coverpoints.svh"

    // main coverpoints: S-level interrupts taken from U-mode and delegated to S
    `ifdef SDTRIG_ITRIGGER_ANY
    `ifdef S_SUPPORTED
        cp_itrigger_u:       cross exec_mode_u, triggernum_itrigger, itrigger_interrupt, itrigger_code_s, trap_delegated, trap_selected, trap_handled_s;   // NTRIG * S interrupts * 2 u
        cp_itrigger_u_other: cross exec_mode_u, triggernum_itrigger, itrigger_interrupt, trap_delegated, trap_not_selected, trap_result_s_other;    // NTRIG * 2 u
    `endif
    `endif
endgroup

covergroup SdtrigU_etrigger_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_trap_coverpoints.svh"

    // main coverpoints: exceptions raised in U-mode (etrigger_route)
    `ifdef SDTRIG_ETRIGGER_ANY
    `ifdef S_SUPPORTED
        cp_etrigger_u:       cross exec_mode_u, triggernum_etrigger, etrigger_exception, trap_selected, etrigger_route, trap_priv;  // NTRIG * U exceptions * 2 u
        cp_etrigger_u_other: cross exec_mode_u, triggernum_etrigger, etrigger_exception, trap_not_selected, trap_result_other;     // NTRIG * 2 u
    `endif
    `endif
endgroup

covergroup SdtrigU_mcontrol6_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_mcontrol6_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    cp_mcontrol6_priv_bits_u:    cross priv_mode_u, triggernum_mcontrol6, priv_bits_sw, priv_bits_outcome;  // NTRIG * 2 outcomes
    cp_mcontrol6_execute_adr:     cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_adr, tdata1_xsl, exec_adr_target;                                                             // NTRIG * 8 xsl * 2 tdata2
    cp_mcontrol6_load_store_adr:  cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_adr, tdata1_xsl, tdata2_ls_adr, store_offset, lw_sw;                                    // NTRIG * 8 xsl * 3 tdata2 * 2 offsets * 2 instrs
    cp_mcontrol6_execute_data:    cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_data, tdata1_xsl, exec_data_target;                                                     // NTRIG * 8 xsl * 2 tdata2
    cp_mcontrol6_load_store_data: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_data, tdata1_xsl, load_store_xlen;                                                            // NTRIG * 8 xsl * 2 instrs
    cp_mcontrol6_execute_size:    cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_select_data, tdata1_xsl_load_store_execute, tdata1_size, tdata2_exec_size, exec_size_target;              // NTRIG * 7 sizes * 2 tdata2 * 2 instrs
    `ifdef SDTRIG_EXEC_ADR_SIZE
        cp_mcontrol6_execute_adr_size: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_select_adr, tdata1_execute_on, exec_adr_size_case; // NTRIG * legal (size, instruction) pairs (up to 8)
    `endif
    cp_mcontrol6_load_store_size: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_select_adr, tdata1_xsl_load_store, tdata1_size_ls, tdata2_adr, load_store_instr;               // NTRIG * 5 sizes * 2 tdata2 * instrs
    cp_mcontrol6_match:           cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_size_any, tdata1_select_data, tdata1_xsl_store, tdata1_match_cmp, store_data_cmp, store_xlen;                   // NTRIG * 4 match * 5 values
    `ifdef SDTRIG_MATCH_NAPOT
        cp_mcontrol6_match_napot: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_size_any, tdata1_select_data, tdata1_xsl_store, tdata1_match_napot, tdata2_napot, store_data_napot, store_xlen; // NTRIG * 2 match * min(maskmax6, XLEN-1) tdata2 * 3 values
    `endif
    `ifdef SDTRIG_MATCH_MASK
        cp_mcontrol6_match_mask:  cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_size_any, tdata1_select_data, tdata1_xsl_store, tdata1_match_mask, store_data_mask, store_xlen;                 // NTRIG * 4 match * 11 values
    `endif
    `ifdef SDTRIG_SIZE_DATA
        cp_mcontrol6_size_data: cross exec_mode_u, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_select_data, tdata1_xsl_store, tdata1_size_data, size_data_case, size_data_outcome; // NTRIG * sizes * 3
    `endif
    `ifdef SDTRIG_MATCH_SIZE_STORE
        cp_mcontrol6_match_size_store: cross exec_mode_u, triggernum_mcontrol6, ms_match, ms_size_data, ms_store_case; // NTRIG * legal matches * legal sizes * 3
    `endif
    `ifdef SDTRIG_MATCH_SIZE_LOAD
        cp_mcontrol6_match_size_load:  cross exec_mode_u, triggernum_mcontrol6, ms_match, ms_size_data, ms_load_case;  // NTRIG * legal matches * legal sizes * 3
    `endif
    `ifdef SDTRIG_CHAIN_3
        cp_mcontrol6_chain_long: cross exec_mode_u, triggernum_chain_end, tdata1_type_mcontrol6, tdata1_u_on, tdata1_chain_disabled, tdata1_select_adr, tdata1_size_any, tdata1_xsl_store, store_xlen, chain_store_x0, chain_store_adr, chain_fired; // chain lengths * 2
    `endif
    `ifdef SDTRIG_CHAIN_ANY_PAIR
    cp_mcontrol6_chain_adr:       cross exec_mode_u, triggernum_chain, tdata1_type_mcontrol6, tdata1_u_on, tdata1_select_data, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_xsl_store, store_data_chain, store_offset, store_xlen;                    // (NTRIG-1) * 2 data * 2 adr
    `endif
    `endif
endgroup

covergroup SdtrigU_textra_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_textra_coverpoints.svh"

    // main coverpoints: sampled on the instruction in U-mode that the armed trigger acts on
    `ifdef UDB_TDATA3_IMPLEMENTED
    `ifdef SDTRIG_TEXTRA_MCONTEXT
        cp_textra_mcontext:       cross exec_mode_u, triggernum, textra_action, mhselect_mcontext, sselect_ignore, mcontext_match;           // NTRIG * 2 types * 2
    `endif
    `ifdef SDTRIG_TEXTRA_SCONTEXT
        cp_textra_scontext:       cross exec_mode_u, triggernum, textra_action, sselect_scontext, sbytemask, scontext_match;                 // NTRIG * 2 types * 5 (RV32 3) masks * 2
        cp_textra_scontext_all:   cross exec_mode_u, triggernum, textra_action, sselect_scontext, sbytemask_all, scontext_match_only;        // NTRIG * 2 types
    `endif
    `ifdef SDTRIG_TEXTRA_MCONTEXT
    `ifdef SDTRIG_TEXTRA_SCONTEXT
        cp_textra_double_context: cross exec_mode_u, triggernum, textra_action, mhselect, sselect, mcontext_match, scontext_match;           // NTRIG * 2 types * 16
    `endif
    `endif
    `endif
endgroup

function void sdtrigu_sample(int hart, int issue, ins_t ins);
    // Each covergroup is sampled only on the records its crosses can hit (CSR accesses, traps, and the
    // instructions that triggers act on), which keeps coverage of the long U-mode runs fast.
    logic [6:0] op;
    logic       csr, trap, ldst;
    op   = ins.current.insn[6:0];
    csr  = op == 7'b1110011 && ins.current.insn[14:12] != 3'b000;
    trap = ins.current.csr_wb[CSR_MCAUSE] || ins.current.csr_wb[CSR_SCAUSE];
    ldst = op == 7'b0000011 || op == 7'b0100011 || op == 7'b0000111 || op == 7'b0100111 || ins.current.insn[1:0] != 2'b11;
    if (trap) SdtrigU_cg.sample(ins);
    if (csr) SdtrigU_access_cg.sample(ins);
    if (csr || trap) SdtrigU_icount_cg.sample(ins);
    if (op == 7'b0101111) SdtrigU_a_cg.sample(ins);
    if (op == 7'b0001111 || op == 7'b0010011) SdtrigU_cache_operations_cg.sample(ins);
    `ifdef ZVL32B_SUPPORTED
        if (op == 7'b0000111 || op == 7'b0100111) SdtrigU_combined_accesses_cg.sample(ins);
    `endif
    if (trap) SdtrigU_itrigger_cg.sample(ins);
    if (trap) SdtrigU_etrigger_cg.sample(ins);
    if (trap || ldst || op == 7'b0110011 || op == 7'b0010011) SdtrigU_mcontrol6_cg.sample(ins);
    if (csr || ldst || op == 7'b0010011) SdtrigU_textra_cg.sample(ins);
endfunction

`undef SDTRIG_SUITE_U
`undef SDTRIG_ICOUNT_MODE_BIT
`undef SDTRIG_MCONTROL6_MODE_BIT
