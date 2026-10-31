///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Angela Zheng, angela20061015@gmail.com, 10 September 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SDTRIGSM
// suite-local defines for the shared coverpoints, undefined at the end of this file
`define SDTRIG_SUITE_SM           // the tests run in M-mode
`define SDTRIG_ICOUNT_MODE_BIT 9  // icount tdata1.m: the tests count in M-mode
`include "general/RISCV_coverage_sdtrig_derived.svh"
`include "general/RISCV_coverage_sdtrig_functions.svh"

// An optional trigger CSR that this hart does not implement (cp_csr_unimplemented)
`ifndef UDB_TDATA2_IMPLEMENTED
    `define SDTRIG_CSR_UNIMPLEMENTED
`endif
`ifndef UDB_TDATA3_IMPLEMENTED
    `define SDTRIG_CSR_UNIMPLEMENTED
`endif
`ifndef UDB_TCONTROL_IMPLEMENTED
    `define SDTRIG_CSR_UNIMPLEMENTED
`endif
`ifndef UDB_MCONTEXT_IMPLEMENTED
    `define SDTRIG_CSR_UNIMPLEMENTED
`endif
`ifndef UDB_SCONTEXT_IMPLEMENTED
    `define SDTRIG_CSR_UNIMPLEMENTED
`endif
`ifndef UDB_HCONTEXT_IMPLEMENTED
    `define SDTRIG_CSR_UNIMPLEMENTED
`endif

covergroup SdtrigSm_trig_module_reg_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_reg_coverpoints.svh"

    `ifdef SDTRIG_CSR_UNIMPLEMENTED
        csr_unimplemented: coverpoint ins.current.insn[31:20] {
            type_option.weight = 0;
            `ifndef UDB_TDATA2_IMPLEMENTED
                bins tdata2 = {CSR_TDATA2};
            `endif
            `ifndef UDB_TDATA3_IMPLEMENTED
                bins tdata3 = {CSR_TDATA3};
            `endif
            `ifndef UDB_TCONTROL_IMPLEMENTED
                bins tcontrol = {CSR_TCONTROL};
            `endif
            `ifndef UDB_MCONTEXT_IMPLEMENTED
                bins mcontext = {CSR_MCONTEXT};
            `endif
            `ifndef UDB_SCONTEXT_IMPLEMENTED
                bins scontext = {CSR_SCONTEXT};
            `endif
            `ifndef UDB_HCONTEXT_IMPLEMENTED
                bins hcontext = {CSR_HCONTEXT};
            `endif
        }
    `endif

    // main coverpoints
    cp_tdata_write:           cross priv_mode_m, triggernum, type_disabled, csr_tdata, csr_access;          // NTRIG * 3 CSRs * 2 values
    cp_csr_access_global:     cross priv_mode_m, csr_global_reg, csr_access;                                // implemented global CSRs * 2 values
    cp_csr_access_local:      cross priv_mode_m, triggernum, csr_local_reg, csr_access;                     // NTRIG * 4 CSRs * 2 values
    cp_tselect_trigs:         cross priv_mode_m, triggernum, csrr, csr_tinfo, tinfo_exists, tinfo_version;  // NTRIG
    cp_tselect_nonexistent:   cross priv_mode_m, csrw, csr_tselect, tselect_past_last;                      // 1
    `ifdef SDTRIG_MCONTROL6_ANY
        cp_tdata1_mode_hardwired: cross priv_mode_m, triggernum_mcontrol6, csrw, csr_tdata1, tdata1_type_six, priv_bits;  // mcontrol6 triggers
    `endif
    cp_tinfo_read_only:       cross priv_mode_m, triggernum, csr_tinfo, csr_access;                         // NTRIG
    cp_tdata1_dmode:          cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_write_type, dmode_written, dmode_after;  // NTRIG * 2 types
    `ifdef SDTRIG_CSR_UNIMPLEMENTED
        cp_csr_unimplemented: cross priv_mode_m, csr_unimplemented, csr_read_write, illegal_insn_trap;     // unimplemented optional CSRs * 2 accesses
    `endif
endgroup

`ifdef UDB_TCONTROL_IMPLEMENTED
// cp_tcontrol_enable, for add x0, x1, x2 watched by an M-mode execute trigger: 1 = it ran with tcontrol.mte = 0 and
// nothing fired; 2 = with mte = 1 the trigger fired on it (mepc = tdata2); 0 = anything else
function automatic logic [1:0] sdtrig_tcontrol_exec_outcome(ins_t ins);
    logic mte = get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tcontrol", "mte")[0];
    if (sdtrig_exec_fired(ins) && ins.current.csr[CSR_MEPC] == ins.current.csr[CSR_TDATA2]) return mte ? 2'd2 : 2'd0;
    if (ins.current.insn == 32'h00208033 && ins.current.pc_rdata == ins.current.csr[CSR_TDATA2]) return mte ? 2'd0 : 2'd1;
    return 2'd0;
endfunction

covergroup SdtrigSm_tcontrol_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"

    mte: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tcontrol", "mte")[0] {
        bins disabled = {1'b0};
        bins enabled  = {1'b1};
    }
    mpte: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tcontrol", "mpte")[0] {
        bins disabled = {1'b0};
        bins enabled  = {1'b1};
    }
    tcontrol_exec_outcome: coverpoint sdtrig_tcontrol_exec_outcome(ins) {
        bins mte_0_not_fired = {2'd1};
        bins mte_1_fired     = {2'd2};
    }

    // main coverpoints
    `ifdef UDB_SDTRIG_BREAKPOINT_REENTRANCY_USE_TCONTROL
        `ifdef SDTRIG_MCONTROL6_ANY
            cp_tcontrol_enable: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_execute_on, tdata1_select_adr, tdata1_action_breakpoint, tdata1_chain_disabled, tcontrol_exec_outcome;  // NTRIG * 2 mte
        `endif
    `endif
    cp_tcontrol_mtrap:      cross priv_mode_m, mte, mpte, illegal_insn_trap;                                                  // 2 mte * 2 mpte
    cp_tcontrol_mret:       cross priv_mode_m, mte, mpte, mret;                                                               // 2 mte * 2 mpte
endgroup
`endif

covergroup SdtrigSm_access_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_access_coverpoints.svh"

    // main coverpoints
    cp_csr_access_common: cross priv_mode_m, triggernum, tdata1_type, csr_common_reg, csr_access_common;  // NTRIG * 5 types * implemented CSRs (4-8) * 5 accesses
endgroup

covergroup SdtrigSm_icount_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_icount_coverpoints.svh"

    `ifndef UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1
        // cp_icount_self_write: csrw tdata1 = icount with count = 100 on an icount trigger armed with count = 1, m = 1
        icount_self_write: coverpoint {sdtrig_icount_count(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")) == 1,
                                       get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")[9],
                                       ins.current.rs1_val[XLEN-1:XLEN-4] == 4'd3, sdtrig_icount_count(ins.current.rs1_val) == 100} {
            type_option.weight = 0;
            bins count_one_rewritten = {4'b1111};
        }
    `endif

    // main coverpoints
    `ifdef SDTRIG_ICOUNT_ANY
    `ifdef UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1
        cp_icount_hardwired: cross priv_mode_m, triggernum_icount, csrr, csr_tdata1, icount_readback, armed_hardwired, hardwired_result;  // NTRIG
    `else
        cp_icount_instr:      cross priv_mode_m, triggernum_icount, csrr, csr_tdata1, icount_readback, armed_gt1, icount_count_result;  // NTRIG * 2 m
        cp_icount_instr_fire: cross priv_mode_m, triggernum_icount, icount_fired, fired_gt1_mode;                                          // NTRIG
        cp_icount_eq0:        cross priv_mode_m, triggernum_icount, csrr, csr_tdata1, icount_readback, armed_zero_mode, icount_eq0_result; // NTRIG * 2 pending
        cp_icount_eq0_fire:   cross priv_mode_m, triggernum_icount, icount_fired, fired_zero_pending, csrw, csr_tdata1;                // NTRIG; the tdata1 write that arms the pending trigger: it fires before the next instruction
        cp_icount_self_write: cross priv_mode_m, triggernum_icount, csrw, csr_tdata1, icount_self_write;                               // NTRIG
    `endif
    cp_icount_trap:           cross priv_mode_m, triggernum_icount, csrr, csr_tdata1, icount_readback, armed_one, icount_count_result;   // NTRIG * 2 m
    cp_icount_trap_fire:      cross priv_mode_m, triggernum_icount, icount_fired, fired_one_mode, mret;                                     // NTRIG
    `endif
endgroup

covergroup SdtrigSm_a_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_a_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    cp_lrsc_addr: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_select_adr, tdata2_rs1, tdata1_xsl_one, lrsc_op, a_outcome;        // NTRIG * 2 tdata2 * 3 xsl * 2 (RV64 4) ops
    cp_lrsc_data: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_select_data, a_tdata2_data, tdata1_xsl_one, lrsc_op_xlen, a_outcome; // NTRIG * 2 tdata2 * 3 xsl * 2 ops
    cp_amo:       cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_select_adr, tdata2_rs1, tdata1_xsl_one, amo_op, a_outcome;         // NTRIG * 2 tdata2 * 3 xsl * 9 (RV64 18) ops
    `endif
endgroup

covergroup SdtrigSm_cache_operations_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_cache_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    `ifdef ZICBOM_SUPPORTED
        cp_cache_zicbom: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, cbo_tdata2, cbo_select, tdata1_size, tdata1_xsl_one, cbom_op, cbo_outcome;                  // NTRIG * 4 tdata2 * 2 select * sizes * 3 xsl * 3 ops
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cp_cache_zicboz: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, cbo_tdata2, cbo_select, tdata1_size, tdata1_xsl_one, cboz_op, cbo_outcome;                  // NTRIG * 4 tdata2 * 2 select * sizes * 3 xsl
    `endif
    `ifdef ZICBOP_SUPPORTED
        cp_cache_zicbop: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata2_rs1, cbo_select, tdata1_size_any, tdata1_xsl_load_store, prefetch_op, cbo_outcome; // NTRIG * 2 tdata2 * 2 select * 3 ops
    `endif
    `endif
endgroup

`ifdef ZVL32B_SUPPORTED
covergroup SdtrigSm_combined_accesses_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_vector_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    cp_vector_load_store: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_select_adr, tdata2_rs1, tdata1_size, vec_vl_one, vec_unmasked, vec_access, vec_xsl, vec_outcome;  // NTRIG * 2 tdata2 * sizes * 6 (Zve64x 8) accesses
    cp_vector_accesses:   cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_select_adr, vec_tdata2, tdata1_size_any, vec_vl, vec_unmasked, vec_access, vec_xsl, vec_outcome;    // NTRIG * 3 tdata2 * 2 vl * 6 (8) accesses
    cp_vector_mask:       cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_select_adr, vec_tdata2_plus_8, tdata1_size_any, vec_vl_reaches_8, vec_masked, vec_element_8, vec_access, vec_xsl, vec_outcome; // NTRIG * 2 mask states * 6 (8) accesses
    `endif
endgroup
`endif

covergroup SdtrigSm_itrigger_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_trap_coverpoints.svh"

    // interrupts taken in M from M
    itrigger_code_m: coverpoint sdtrig_trap_cause(ins)[7:0] {
        type_option.weight = 0;
        `ifdef UDB_MSI_INTR_IMPL
            `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_3 bins msi = {8'd3}; `endif
        `endif
        `ifdef UDB_MTI_INTR_IMPL
            `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_7 bins mti = {8'd7}; `endif
        `endif
        `ifdef UDB_MEI_INTR_IMPL
            `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_11 bins mei = {8'd11}; `endif
        `endif
        `ifdef S_SUPPORTED
            `ifdef UDB_SSI_INTR_IMPL
                `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_1 bins ssi = {8'd1}; `endif
            `endif
            `ifdef UDB_STI_INTR_IMPL
                `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_5 bins sti = {8'd5}; `endif
            `endif
            `ifdef UDB_SEI_INTR_IMPL
                `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_9 bins sei = {8'd9}; `endif
            `endif
            `ifdef SSCOFPMF_SUPPORTED
                `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_13 bins lcofi = {8'd13}; `endif
            `endif
        `endif
    }

    // main coverpoints
    `ifdef SDTRIG_ITRIGGER_ANY
    cp_itrigger_m:           cross exec_mode_m, triggernum_itrigger, itrigger_interrupt, itrigger_code_m, trap_not_delegated, trap_selected, trap_result_m;           // NTRIG * interrupts * 2 m
    cp_itrigger_m_other:     cross exec_mode_m, triggernum_itrigger, itrigger_interrupt, trap_not_delegated, trap_not_selected, trap_result_m;                         // NTRIG * 2 m
    `ifdef S_SUPPORTED
        cp_itrigger_s:       cross exec_mode_s, triggernum_itrigger, itrigger_interrupt, itrigger_code_s, trap_delegated, trap_selected, trap_result_s;               // NTRIG * S interrupts * 2 s
        cp_itrigger_s_other: cross exec_mode_s, triggernum_itrigger, itrigger_interrupt, trap_delegated, trap_not_selected, trap_result_s_other;                       // NTRIG * 2 s
        `ifdef U_SUPPORTED
            cp_itrigger_u:       cross exec_mode_u, triggernum_itrigger, itrigger_interrupt, itrigger_code_s, trap_delegated, trap_selected, trap_result_s;           // NTRIG * S interrupts * 2 u
            cp_itrigger_u_other: cross exec_mode_u, triggernum_itrigger, itrigger_interrupt, trap_delegated, trap_not_selected, trap_result_s_other;                   // NTRIG * 2 u
        `endif
    `endif
    `endif
endgroup

covergroup SdtrigSm_etrigger_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_trap_coverpoints.svh"

    // exceptions raised in M. Page faults come from loads and stores with MPRV = 1, MPP = U.
    etrigger_code_m: coverpoint sdtrig_trap_cause(ins)[7:0] {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_1 bins iacc = {8'd1}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_2 bins ill  = {8'd2}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_5 bins lacc = {8'd5}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_7 bins sacc = {8'd7}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_11 bins ecm  = {8'd11}; `endif
        `ifdef UDB_MXLEN_64
            `ifdef SV39_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `else
            `ifdef SV32_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `endif
    }
    // exceptions raised in S, handled in M
    etrigger_code_s: coverpoint sdtrig_trap_cause(ins)[7:0] {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_1 bins iacc = {8'd1}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_2 bins ill  = {8'd2}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_5 bins lacc = {8'd5}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_7 bins sacc = {8'd7}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_9 bins ecs  = {8'd9}; `endif
        `ifdef UDB_MXLEN_64
            `ifdef SV39_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_12 bins ipf = {8'd12}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `else
            `ifdef SV32_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_12 bins ipf = {8'd12}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `endif
    }
    // exceptions raised in U, handled in M
    etrigger_code_u: coverpoint sdtrig_trap_cause(ins)[7:0] {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_1 bins iacc = {8'd1}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_2 bins ill  = {8'd2}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_5 bins lacc = {8'd5}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_7 bins sacc = {8'd7}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_8 bins ecu  = {8'd8}; `endif
        `ifdef UDB_MXLEN_64
            `ifdef SV39_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_12 bins ipf = {8'd12}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `else
            `ifdef SV32_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_12 bins ipf = {8'd12}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `endif
    }
    // exceptions raised in S and delegated to S. ecall from S is not: the T-SBI return to M is itself one.
    // A delegated illegal instruction is not either: a DUT that emulates the time CSR forwards it in software.
    etrigger_code_s_deleg: coverpoint sdtrig_trap_cause(ins)[7:0] {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_1 bins iacc = {8'd1}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_5 bins lacc = {8'd5}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_7 bins sacc = {8'd7}; `endif
        `ifdef UDB_MXLEN_64
            `ifdef SV39_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_12 bins ipf = {8'd12}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `else
            `ifdef SV32_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_12 bins ipf = {8'd12}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `endif
    }
    // exceptions raised in U and delegated to S
    etrigger_code_u_deleg: coverpoint sdtrig_trap_cause(ins)[7:0] {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_1 bins iacc = {8'd1}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_5 bins lacc = {8'd5}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_7 bins sacc = {8'd7}; `endif
        `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_8 bins ecu  = {8'd8}; `endif
        `ifdef UDB_MXLEN_64
            `ifdef SV39_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_12 bins ipf = {8'd12}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `else
            `ifdef SV32_SUPPORTED
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_12 bins ipf = {8'd12}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_13 bins lpf = {8'd13}; `endif
                `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_15 bins spf = {8'd15}; `endif
            `endif
        `endif
    }

    // main coverpoints
    `ifdef SDTRIG_ETRIGGER_ANY
    cp_etrigger_m:               cross exec_mode_m, triggernum_etrigger, etrigger_exception, etrigger_code_m, trap_selected, trap_result_m;                             // NTRIG * M exceptions * 2 m
    cp_etrigger_m_other:         cross exec_mode_m, triggernum_etrigger, etrigger_exception, trap_not_selected, trap_result_m;                                           // NTRIG * 2 m
    `ifdef S_SUPPORTED
        cp_etrigger_s:           cross exec_mode_s, triggernum_etrigger, etrigger_exception, etrigger_code_s, trap_not_delegated, trap_selected, trap_result_m;         // NTRIG * S exceptions * 2 s
        cp_etrigger_s_deleg:     cross exec_mode_s, triggernum_etrigger, etrigger_exception, etrigger_code_s_deleg, trap_delegated, trap_selected, trap_result_s;       // NTRIG * delegated S exceptions * 2 s
        cp_etrigger_s_other:     cross exec_mode_s, triggernum_etrigger, etrigger_exception, trap_not_delegated, trap_not_selected, trap_result_m;                       // NTRIG * 2 s
        `ifdef U_SUPPORTED
            cp_etrigger_u:       cross exec_mode_u, triggernum_etrigger, etrigger_exception, etrigger_code_u, trap_not_delegated, trap_selected, trap_result_m;     // NTRIG * U exceptions * 2 u
            cp_etrigger_u_deleg: cross exec_mode_u, triggernum_etrigger, etrigger_exception, etrigger_code_u_deleg, trap_delegated, trap_selected, trap_result_s;   // NTRIG * delegated U exceptions * 2 u
            cp_etrigger_u_other: cross exec_mode_u, triggernum_etrigger, etrigger_exception, trap_not_delegated, trap_not_selected, trap_result_m;                   // NTRIG * 2 u
        `endif
    `endif
    `endif
endgroup

covergroup SdtrigSm_mcontrol6_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_mcontrol6_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    cp_mcontrol6_priv_mode: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_adr, tdata1_xsl_store, tdata2_adr, sw { // NTRIG * 2 m modes
        ignore_bins no_match = binsof(tdata2_adr.zero);
    }
    cp_mcontrol6_execute_adr:     cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_adr, tdata1_xsl, exec_adr_target;                                                             // NTRIG * 8 xsl * 2 tdata2
    cp_mcontrol6_load_store_adr:  cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_adr, tdata1_xsl, tdata2_ls_adr, store_offset, lw_sw;                                    // NTRIG * 8 xsl * 3 tdata2 * 2 offsets * 2 instrs
    cp_mcontrol6_execute_data:    cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_data, tdata1_xsl, exec_data_target;                                                     // NTRIG * 8 xsl * 2 tdata2
    cp_mcontrol6_load_store_data: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_select_data, tdata1_xsl, load_store_xlen;                                                            // NTRIG * 8 xsl * 2 instrs
    cp_mcontrol6_execute_size:    cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_select_data, tdata1_xsl_load_store_execute, tdata1_size, tdata2_exec_size, exec_size_target;              // NTRIG * 7 sizes * 2 tdata2 * 2 instrs
    `ifdef SDTRIG_EXEC_ADR_SIZE
        cp_mcontrol6_execute_adr_size: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_select_adr, tdata1_execute_on, exec_adr_size_case; // NTRIG * legal (size, instruction) pairs (up to 8)
    `endif
    cp_mcontrol6_load_store_size: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_match_equal, tdata1_select_adr, tdata1_xsl_load_store, tdata1_size_ls, tdata2_adr, load_store_instr;               // NTRIG * 5 sizes * 2 tdata2 * instrs
    cp_mcontrol6_match:           cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_size_any, tdata1_select_data, tdata1_xsl_store, tdata1_match_cmp, store_data_cmp, store_xlen;                   // NTRIG * 4 match * 5 values
    `ifdef SDTRIG_MATCH_NAPOT
        cp_mcontrol6_match_napot: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_size_any, tdata1_select_data, tdata1_xsl_store, tdata1_match_napot, tdata2_napot, store_data_napot, store_xlen; // NTRIG * 2 match * min(maskmax6, XLEN-1) tdata2 * 3 values
        cp_mcontrol6_napot_allones: cross priv_mode_m, triggernum_mcontrol6, csrw, csr_tdata2, tdata1_type_mcontrol6, tdata1_match_napot, tdata2_write_ones; // NTRIG * 2 match
    `endif
    `ifdef SDTRIG_MATCH_MASK
        cp_mcontrol6_match_mask:  cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_size_any, tdata1_select_data, tdata1_xsl_store, tdata1_match_mask, store_data_mask, store_xlen;                 // NTRIG * 4 match * 11 values
    `endif
    `ifdef SDTRIG_SIZE_DATA
        cp_mcontrol6_size_data: cross priv_mode_m, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_select_data, tdata1_xsl_store, tdata1_size_data, size_data_case, size_data_outcome; // NTRIG * sizes * 3
    `endif
    `ifdef SDTRIG_MATCH_SIZE_STORE
        cp_mcontrol6_match_size_store:   cross priv_mode_m, triggernum_mcontrol6, ms_match, tdata1_size_data, ms_store_case;  // NTRIG * legal matches * legal sizes * 3
    `endif
    `ifdef SDTRIG_MATCH_SIZE_LOAD
        cp_mcontrol6_match_size_load:    cross priv_mode_m, triggernum_mcontrol6, ms_match, tdata1_size_data, ms_load_case;   // NTRIG * legal matches * legal sizes * 3
    `endif
    `ifdef SDTRIG_MATCH_SIZE_EXEC
        cp_mcontrol6_match_size_execute: cross priv_mode_m, triggernum_mcontrol6, ms_match_exec, ms_size_exec, ms_exec_case; // NTRIG * legal matches * sizes 2/3 * 2
        `ifdef SDTRIG_MATCH_SIZE_EXEC16
            cp_mcontrol6_match_size_execute_other: cross priv_mode_m, triggernum_mcontrol6, ms_match_exec, ms_size_exec16, ms_exec_other; // NTRIG * legal matches (RV64: but 5, 13)
        `endif
    `endif
    `ifdef SDTRIG_CHAIN_3
        cp_mcontrol6_chain_long: cross priv_mode_m, triggernum_chain_end, tdata1_type_mcontrol6, tdata1_m_on, tdata1_chain_disabled, tdata1_select_adr, tdata1_size_any, tdata1_xsl_store, store_xlen, chain_store_x0, chain_store_adr, chain_fired; // chain lengths * 2
    `endif
    `ifdef SDTRIG_CHAIN_ANY_PAIR
    cp_mcontrol6_chain_adr:       cross priv_mode_m, triggernum_chain, tdata1_type_mcontrol6, tdata1_m_on, tdata1_select_data, tdata1_chain_disabled, tdata1_match_equal, tdata1_size_any, tdata1_xsl_store, store_data_chain, store_offset, store_xlen;                    // (NTRIG-1) * 2 data * 2 adr
    `endif
    `endif
endgroup

covergroup SdtrigSm_textra_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_textra_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_trap_coverpoints.svh"

    // itrigger/etrigger textra: the trap the trigger watches, handled in S, fired into M iff the context matches
    textra_trap_mcontext: coverpoint sdtrig_textra_trap_outcome(ins) {
        type_option.weight = 0;
        bins mismatch_suppressed = {3'b01_0};
        bins match_fired         = {3'b01_1};
    }
    textra_trap_scontext: coverpoint sdtrig_textra_trap_outcome(ins) {
        type_option.weight = 0;
        bins mismatch_suppressed = {3'b10_0};
        bins match_fired         = {3'b10_1};
    }

    // main coverpoints
    `ifdef UDB_TDATA3_IMPLEMENTED
    `ifdef SDTRIG_TEXTRA_MCONTEXT
        cp_textra_mcontext:       cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_write_type, mhselect_mcontext, sselect_ignore, mcontext_match;                       // NTRIG * 2 types * 2
    `endif
    `ifdef SDTRIG_TEXTRA_SCONTEXT
        cp_textra_scontext:       cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_write_type, sselect_scontext, sbytemask, scontext_match;                          // NTRIG * 2 types * 5 (RV32 3) masks * 2
        cp_textra_scontext_all:   cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_write_type, sselect_scontext, sbytemask_all, scontext_match_only;                 // NTRIG * 2 types
    `endif
    `ifdef SDTRIG_TEXTRA_MCONTEXT
    `ifdef SDTRIG_TEXTRA_SCONTEXT
        cp_textra_double_context: cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_write_type, mhselect, sselect, mcontext_match, scontext_match;              // NTRIG * 2 types * 16
    `endif
    `endif
    `ifdef S_SUPPORTED
        `ifdef UDB_SDTRIG_TEXTRA_SSELECT_ASID_MATCH
            cp_textra_asid:           cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_write_type, mhselect_ignore, sselect_asid, asid_match;                      // NTRIG * 2 types * 2
            cp_textra_asid_sbytemask: cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_write_type, mhselect_ignore, sselect_asid, sbytemask_all, asid_match;       // NTRIG * 2 types * 2
        `endif
        `ifdef SDTRIG_TEXTRA_MCONTEXT
            `ifdef SDTRIG_ITRIGGER_ANY
                cp_textra_itrigger_mcontext: cross exec_mode_s, triggernum_itrigger, itrigger_interrupt, trap_delegated, trap_selected, textra_trap_mcontext;     // NTRIG * 2
            `endif
            `ifdef SDTRIG_ETRIGGER_ANY
                cp_textra_etrigger_mcontext: cross exec_mode_s, triggernum_etrigger, etrigger_exception, trap_delegated, trap_selected, textra_trap_mcontext;     // NTRIG * 2
            `endif
        `endif
        `ifdef SDTRIG_TEXTRA_SCONTEXT
            `ifdef SDTRIG_ITRIGGER_ANY
                cp_textra_itrigger_scontext: cross exec_mode_s, triggernum_itrigger, itrigger_interrupt, trap_delegated, trap_selected, textra_trap_scontext;     // NTRIG * 2
            `endif
            `ifdef SDTRIG_ETRIGGER_ANY
                cp_textra_etrigger_scontext: cross exec_mode_s, triggernum_etrigger, etrigger_exception, trap_delegated, trap_selected, textra_trap_scontext;     // NTRIG * 2
            `endif
        `endif
    `endif
    `ifndef H_SUPPORTED
        cp_textra_mhselect_no_h:  cross priv_mode_m, triggernum, csrw, csr_tdata3, armed_type, mhselect_written, mhselect_legal;                             // NTRIG * 2 types * 6
    `endif
    `endif
endgroup

covergroup SdtrigSm_address_matches_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_xlate_coverpoints.svh"

    // main coverpoints
    `ifdef SDTRIG_MCONTROL6_ANY
    cp_tdata2_translate:          cross priv_mode_m, triggernum_mcontrol6, csrr, csr_tdata2, tdata1_type_mcontrol6, tdata1_select_adr, tdata2_xlate_value;                       // NTRIG * (2 * VA modes + 1)
    `ifdef S_SUPPORTED
        cp_tdata2_translate_exec: cross priv_mode_s, triggernum_mcontrol6, tdata1_type_mcontrol6, tdata1_select_adr, tdata1_execute_on, satp_xlate_mode, tdata2_xlate_exec; // NTRIG * VA modes * 2
    `endif
    `endif
endgroup

function void sdtrigsm_sample(int hart, int issue, ins_t ins);
    SdtrigSm_trig_module_reg_cg.sample(ins);
    SdtrigSm_access_cg.sample(ins);
    SdtrigSm_icount_cg.sample(ins);
    SdtrigSm_a_cg.sample(ins);
    SdtrigSm_cache_operations_cg.sample(ins);
    `ifdef ZVL32B_SUPPORTED
        SdtrigSm_combined_accesses_cg.sample(ins);
    `endif
    SdtrigSm_itrigger_cg.sample(ins);
    SdtrigSm_etrigger_cg.sample(ins);
    SdtrigSm_mcontrol6_cg.sample(ins);
    SdtrigSm_textra_cg.sample(ins);
    SdtrigSm_address_matches_cg.sample(ins);
    `ifdef UDB_TCONTROL_IMPLEMENTED
        SdtrigSm_tcontrol_cg.sample(ins);
    `endif
endfunction

`undef SDTRIG_SUITE_SM
`undef SDTRIG_ICOUNT_MODE_BIT
