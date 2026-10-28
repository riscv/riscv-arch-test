///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) coverage for the Sm, S, U and H groups
//
// Written: Umer Shahid umer@riscv.org 2026
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICFISS

// The PMP test covers the 4 KiB shadow stack page with PMP entry 0 as one NAPOT region and the
// rest of memory with entry 1. It needs NAPOT, a granularity of at most 4 KiB (G <= 12) and two
// usable entries.
`ifdef UDB_PMP_NAPOT_SUPPORTED
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_0
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_1
    `ifdef UDB_PMP_GRANULARITY_2
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_3
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_4
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_5
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_6
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_7
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_8
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_9
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_10
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_11
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_12
        `define ZICFISS_PMP_TEST
    `endif
`endif
`endif
`endif

`ifndef EXCLUDE_SM
covergroup Zicfiss_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfiss_coverpoints.svh"

    // menvcfg.SSE x senvcfg.SSE. menvcfg.SSE=0 forces senvcfg.SSE read-only zero. Clearing menvcfg.SSE does not re-log
    // senvcfg, so until the next senvcfg write the trace can still show senvcfg.SSE=1; ANDing with
    // menvcfg.SSE gives the effective value. An explicit senvcfg write is logged legalized.
    sse_state: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                           ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1 &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))} {
        bins men0_sen0 = {2'b00};
        bins men1_sen0 = {2'b10};
        bins men1_sen1 = {2'b11};
    }
    // pmp0cfg R is bit 0, W is bit 1. Shadow stack instructions require read-write.
    // R=0 with W=1 is a reserved combination, so it cannot be configured.
    `ifdef ZICFISS_PMP_TEST
        pmp0_rw: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "pmpcfg0", "pmp0cfg_xwr")[1:0] {
            bins no_perm    = {2'b00};
            bins read_only  = {2'b01};
            bins read_write = {2'b11};
        }
    `endif
    senvcfg_csr: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
    }
    `ifdef H_SUPPORTED
        henvcfg_csr: coverpoint ins.current.insn[31:20] {
            bins henvcfg = {CSR_HENVCFG};
        }
    `endif
    // Ordinary word/doubleword load and store, for the SS page encoding check.
    `ifdef UDB_MXLEN_64
        ls_op: coverpoint ins.current.insn {
            wildcard bins load  = {LD};
            wildcard bins store = {SD};
        }
    `else
        ls_op: coverpoint ins.current.insn {
            wildcard bins load  = {LW};
            wildcard bins store = {SW};
        }
    `endif
    `ifdef SVPBMT_SUPPORTED
        // pte.PBMT is bits [62:61]: 00 PMA, 10 IO. IO is non-idempotent.
        pte_pbmt_pma_io: coverpoint ins.current.pte_d[62:61] {
            bins pma = {2'b00};
            bins io  = {2'b10};
        }
    `endif
    // mstatus.MPRV with MPP=S makes M-mode loads and stores S-mode accesses.
    // The effective privilege mode stays M with MPRV=0, or with MPRV=1 and MPP=M.
    mprv_eff_m: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv")[0],
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
        wildcard bins mprv_clear = {3'b0??};
        bins mprv_mpp_m          = {3'b111};
    }
    mprv_mpp_s: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv")[0],
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
        bins mprv_mpp_s = {3'b101};
    }

    // ── Enable-chain building blocks ──────────────────────────────────────
    // Zicfiss is inactive in S-mode only while menvcfg.SSE=0.
    s_sse_inactive: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
    }

    // ── Translation-mode building blocks ──────────────────────────────────
    // SSAMOSWAP must fault at M regardless of satp.MODE, so sweep Bare vs non-Bare.
    `ifdef UDB_MXLEN_64
        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
            bins bare     = {4'b0000};
            bins translating = {[4'b1000:4'b1011]};
        }
        satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
            bins bare = {4'b0000};
        }
    `else
        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins bare        = {1'b0};
            bins translating = {1'b1};
        }
        satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins bare = {1'b0};
        }
    `endif
    // Zicfiss active in the mode the instruction runs in: menvcfg.SSE=1, and senvcfg.SSE=1 too in U-mode.
    ss_active_below_m: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                                   ((ins.prev.mode == 2'b01) ||
                                    (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))) {
        bins active = {1'b1};
    }
    // ── Main coverpoints ──────────────────────────────────────────────────
    // SSAMOSWAP faults whenever the effective privilege mode is M — sweep every axis that might
    // wrongly be treated as a precondition, and MPRV=1 with MPP=M.
    cp_ssamoswap_mmode_fault:      cross priv_mode_m, ssamoswap_instr, menvcfg_sse, satp_mode, mprv_eff_m;
    // With MPRV=1 and MPP=S the effective privilege mode is S (menvcfg.SSE=1): satp.MODE=Bare gives a
    // store/AMO access fault, and with translation the swap completes on the S-mode SS page.
    cp_ssamoswap_mprv_s:           cross priv_mode_m, ssamoswap_instr, mprv_mpp_s, satp_mode;

    // With MPRV=1 and MPP=S the effective privilege mode is S, so SSAMOSWAP follows the S-mode
    // shadow stack rules: it completes on a PBMT=PMA page and faults on a non-idempotent PBMT=IO one.
    `ifdef SVPBMT_SUPPORTED
        cp_ssamoswap_mprv_non_idempotent: cross priv_mode_m, ssamoswap_instr, mprv_mpp_s, pte_ss_page, pte_pbmt_pma_io;
    `endif

    // menvcfg.SSE gates ssp CSR access from S/HS.
    cp_menvcfg_sse_gating:         cross priv_mode_m_s, csrops, ssp_csr, menvcfg_sse;

    // Shadow stack instructions require PMP read-write permission, including SSPOPCHK
    // which only reads. The denied case also proves the PMP fault outranks the
    // software-check exception a value mismatch would raise.
    `ifdef ZICFISS_PMP_TEST
        cp_ss_pmp_permissions:         cross priv_mode_s, ss_mem_instr, pmp0_rw;
    `endif

    // Below M-mode with satp.MODE=Bare, every SS memory access raises a store/AMO access fault.
    cp_ss_satp_bare:               cross priv_mode_s_u, ss_mem_instr, ss_active_below_m, satp_bare;

    // This suite boots to M-mode, which leaves medeleg at zero, so a software-check exception
    // from S-mode is taken in M-mode and reports shadow stack fault (code 3) in mtval, or 0 if
    // the implementation provides no information.
    // Guarded on the trap being taken by this instruction, since the CSR array is persistent.
    sw_check_m: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "mcause")
                iff (ins.current.csr_wb[CSR_MEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mepc", "mepc") == ins.current.pc_rdata)) {
        bins cause_18 = {SOFTWARE_CHECK};
    }
    mtval_ss_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtval", "mtval")
                    iff (ins.current.csr_wb[CSR_MEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mepc", "mepc") == ins.current.pc_rdata)) {
        `ifdef UDB_REPORT_CAUSE_IN_MTVAL_ON_SHADOW_STACK_SOFTWARE_CHECK
            bins ss_fault = {3};
        `else
            bins no_info = {0};
        `endif
    }
    cp_ss_swcheck_mtval:           cross priv_mode_s, ss_pop_instr, sw_check_m, mtval_ss_fault;

    // Zicfiss inactive: MOP-encoded instructions stay inert, even with an ssp that an
    // active instruction would fault on. At M-mode this holds for every SSE state; S-mode
    // is gated by menvcfg.SSE alone. The U-mode leg is cp_ss_instr_inactive_u in ZicfissU.
    cp_ss_instr_inactive_m:        cross priv_mode_m, ss_mop_instr, sse_state, ssp_state;
    cp_ss_instr_inactive_s:        cross priv_mode_s, ss_mop_instr, s_sse_inactive, ssp_state;

    // With menvcfg.SSE=0 the xwr=010 encoding is reserved below M-mode, so ordinary accesses
    // page-fault; with menvcfg.SSE=1 it is an SS page, readable by loads and not writable by stores.
    // senvcfg.SSE does not change the encoding, so U-mode with senvcfg.SSE=0 still sees an SS page.
    cp_menvcfg_sse_ss_page:        cross priv_mode_s_u, ls_op, pte_ss_page, sse_state;

    // Set and clear senvcfg.SSE and henvcfg.SSE under both values of menvcfg.SSE; the signature
    // checks that they read back 0 whenever menvcfg.SSE is 0.
    cp_envcfg_sse_rdonly0_senvcfg: cross priv_mode_m, senvcfg_csr, menvcfg_sse, sse_bit_write;
    // The V=1 leg, henvcfg.SSE=0 forcing senvcfg.SSE read-only zero, belongs to
    // Zicfiss_H_cg (cp_envcfg_sse_rdonly0_virt).
    `ifdef H_SUPPORTED
        cp_envcfg_sse_rdonly0_henvcfg: cross priv_mode_m, henvcfg_csr, menvcfg_sse, sse_bit_write;
    `endif

endgroup
`endif

// ssp[2] is writable only when UXLEN or SXLEN can be 32
`ifdef UDB_UXLEN_32
    `define ZICFISS_SSP_BIT2_WRITABLE
`elsif UDB_SXLEN_32
    `define ZICFISS_SSP_BIT2_WRITABLE
`endif

`ifdef S_SUPPORTED
covergroup Zicfiss_S_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfiss_coverpoints.svh"

    // ── Enable-chain building blocks ──────────────────────────────────────
    // Swept deliberately: at S/HS this must have NO effect on ssp accessibility.
    senvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // menvcfg.SSE=0 forces senvcfg.SSE read-only zero. Clearing menvcfg.SSE does not re-log
    // senvcfg, so until the next senvcfg write the trace can still show senvcfg.SSE=1; ANDing with
    // menvcfg.SSE gives the effective value. An explicit senvcfg write is logged legalized.
    s_sse_state: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                             ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1 &&
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))} {
        bins men0_sen0 = {2'b00};
        bins men1_sen0 = {2'b10};
        bins men1_sen1 = {2'b11};
    }

    // ── Page / alignment building blocks ──────────────────────────────────
    `ifdef SVPBMT_SUPPORTED
        // pte.PBMT is bits [62:61]: 00 PMA, 01 NC, 10 IO. IO is non-idempotent.
        pte_pbmt: coverpoint ins.current.pte_d[62:61] {
            bins pma = {2'b00};
            bins nc  = {2'b01};
            bins io  = {2'b10};
        }
        // Without menvcfg.PBMTE a nonzero PBMT is reserved, so the walk page-faults.
        menvcfg_pbmte: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte") {
            bins disabled = {1'b0};
            bins enabled  = {1'b1};
        }
    `endif
    ordinary_loadops: coverpoint ins.current.insn {
        wildcard bins lb  = {LB};
        wildcard bins lh  = {LH};
        wildcard bins lw  = {LW};
        `ifdef UDB_MXLEN_64
            wildcard bins ld = {LD};
        `endif
    }

    // U/SUM/MXR are part of address translation and resolve before any Zicfiss rule.
    // sstatus.SUM is bit 18, sstatus.MXR is bit 19.
    sstatus_sum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum") {
        bins sum_clear = {1'b0};
        bins sum_set   = {1'b1};
    }
    senvcfg_csr: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
    }

    // ── Main coverpoints ──────────────────────────────────────────────────
    // S-specific gating: menvcfg.SSE gates, senvcfg.SSE must not.
    cp_ssp_csr_gating_s:           cross priv_mode_s, csrops, ssp_csr, s_sse_state;
    // SSAMOSWAP to the SS page is illegal in S-mode only while menvcfg.SSE=0.
    cp_ssamoswap_sse_gating_s:     cross priv_mode_s, ssamoswap_instr, s_sse_state;

    // SS page encoding is recognised only when menvcfg.SSE=1.
    cp_ss_page_enc:                cross priv_mode_s, ss_mem_instr, pte_ss_page, menvcfg_sse {
        // With menvcfg.SSE=0 the SS instructions are inert MOPs and never reach the page.
        ignore_bins inert_when_sse_off = binsof(menvcfg_sse.sse_off);
    }
    cp_ss_page_enc_load:           cross priv_mode_s, ordinary_loadops, pte_ss_page, menvcfg_sse;
    cp_ss_page_enc_store:          cross priv_mode_s, ordinary_storeops, pte_ss_page, menvcfg_sse;

    cp_sspush_s:                   cross priv_mode_s, ss_push_instr, pte_ss_page;
    cp_sspopchk_match_s:           cross priv_mode_s, ss_pop_instr, sspopchk_outcome, pte_ss_page {
        // Mismatching pops trap and are counted in cp_sspopchk_mismatch_s.
        ignore_bins mismatch = binsof(sspopchk_outcome.mismatched);
    }
    cp_sspopchk_mismatch_s:        cross priv_mode_s, ss_pop_instr, sspopchk_outcome, pte_ss_page, stval_ss_fault, scause_sw_check {
        // Matching pops retire without a trap and are counted in cp_sspopchk_match_s.
        ignore_bins match = binsof(sspopchk_outcome.matched);
    }
    cp_sspopchk_fault_priority_s:  cross priv_mode_s, ss_pop_instr, ssp_fault_address;
    cp_ssrdp_s:                    cross priv_mode_s, ssrdp_instr;
    cp_ssamoswap_s:                cross priv_mode_s, ssamoswap_instr, pte_ss_page;
    cp_ss_address_alignment_ssp_s: cross priv_mode_s, ss_push_instr, pte_ss_page, ssp_LSBs;
    cp_ss_address_alignment_pop_s: cross priv_mode_s, ss_pop_instr, pte_ss_page, ssp_LSBs;
    // The misaligned atomicity granule applies only to Zaamo, Zabha and Zacas AMOs
    // (norm:pma_mag_insts), so every misaligned SSAMOSWAP faults.
    cp_ss_address_alignment_swap_s: cross priv_mode_s, ssamoswap_instr, pte_ss_page, ssamoswap_adr_LSBs;
    cp_ss_instr_target_page_s:     cross priv_mode_s, ss_mem_instr, pte_xwr;

    `ifdef SVPBMT_SUPPORTED
        // PBMT=IO makes the page non-idempotent, which SS instructions must reject; NC memory is
        // idempotent. With PBMTE=0 a nonzero PBMT is reserved instead.
        // Known coverage gap: the SSAMOSWAP x PBMT=NC x PBMTE=1 bins are not tested. An
        // implementation may override the AMO PMA of an NC page (norm:Svpbmt_impl_may_override_pmas),
        // so the outcome is implementation-defined, and no UDB parameter yet says which behavior a
        // DUT has.
        cp_ss_non_idempotent_s:    cross priv_mode_s, ss_mem_instr, pte_ss_page, pte_pbmt, menvcfg_pbmte;
    `endif

    // The U/SUM/MXR permission check resolves before any shadow stack rule, so where
    // the two disagree the translation fault is what gets reported.
    cp_ss_page_perm_priority:      cross priv_mode_s, ss_mem_instr, pte_ss_page, pte_u, sstatus_sum, sstatus_mxr;
    cp_ss_page_perm_priority_load: cross priv_mode_s, ordinary_loadops, pte_ss_page, pte_u, sstatus_sum, sstatus_mxr;
    cp_ss_page_perm_priority_store: cross priv_mode_s, ordinary_storeops, pte_ss_page, pte_u, sstatus_sum, sstatus_mxr;

    // Set and clear senvcfg.SSE under both values of menvcfg.SSE; the signature checks that it
    // reads back 0 whenever menvcfg.SSE is 0.
    cp_senvcfg_sse_rdonly0_s:      cross priv_mode_s, senvcfg_csr, menvcfg_sse, sse_bit_write;
    cp_ss_unused_mop_rr7_rs2_s: cross priv_mode_s, mop_rr7_rs2;
    cp_ss_unused_mop_rr7_rs1_s: cross priv_mode_s, mop_rr7_rs1;
    cp_ss_unused_mop_rr7_rd_s: cross priv_mode_s, mop_rr7_rd;
    cp_ss_unused_mop_r28_rs1_s: cross priv_mode_s, mop_r28_rs1;
    cp_ss_unused_mop_r28_rd_s: cross priv_mode_s, mop_r28_rd;
    `ifdef ZCMOP_SUPPORTED
        cp_ss_unused_mop_c_s: cross priv_mode_s, mop_c;
    `endif
    cp_ss_page_access_store_misaligned_s: cross priv_mode_s, ordinary_storeops, store_addr_lsb, pte_ss_page;

endgroup
`endif

`ifdef U_SUPPORTED
covergroup Zicfiss_U_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfiss_coverpoints.svh"

    // ── Instruction building blocks ───────────────────────────────────────
    // The instructions that address memory through ssp.
    ss_stack_instr: coverpoint ins.current.insn {
        wildcard bins sspush_x1     = {SSPUSH_X1};
        wildcard bins sspush_x5     = {SSPUSH_X5};
        wildcard bins sspopchk_x1   = {SSPOPCHK_X1};
        wildcard bins sspopchk_x5   = {SSPOPCHK_X5};
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspush_x1   = {C_SSPUSH_X1};
            wildcard bins c_sspopchk_x5 = {C_SSPOPCHK_X5};
        `endif
    }
    // ── ssp CSR access building blocks ────────────────────────────────────
    ssp_write_pattern: coverpoint ins.current.rs1_val {
        bins all_zeros = {'0};
        bins all_ones  = {'1};
    }
    // ssp[1:0] are read-only zero; sweep what the test tried to write there.
    // Only the register forms can drive an observable low-bit value: for the immediate
    // forms ins.current.rs1_val reports x[uimm], not the immediate itself.
    csr_reg_ops: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }
    ssp_wr_low_bits: coverpoint ins.current.rs1_val[2:0] {
        // auto fills 00 through 11
    }
    // SSPUSH x5 pushes x5; SSPUSH x1 and C.SSPUSH x1 push x1.
    ss_push_value: coverpoint ((ins.current.insn[1:0] == 2'b11 && ins.current.insn[24:20] == 5'd5) ?
                               ins.prev.x_wdata[5] : ins.prev.x_wdata[1]) {
        bins all_zeros = {'0};
        bins all_ones  = {'1};
        `ifdef UDB_MXLEN_64
            bins pattern = {[64'h1 : 64'h7FFFFFFFFFFFFFFF]};
        `else
            bins pattern = {[32'h1 : 32'h7FFFFFFF]};
        `endif
    }

    // ── SSAMOSWAP data-shape building blocks ──────────────────────────────
    // RV64 SSAMOSWAP.W sign-extends the loaded word: MSB drives the upper half.
    swap_loaded_msb: coverpoint ins.current.rd_val[31] {
        bins msb_zero = {1'b0};
        bins msb_one  = {1'b1};
    }
    // Only rs2[31:0] is stored by SSAMOSWAP.W — prove rs2[63:32] was non-zero
    // at least once so the "upper bits ignored" case is actually exercised.
    `ifdef UDB_MXLEN_64
        swap_rs2_upper: coverpoint (|ins.current.rs2_val[63:32]) {
            bins upper_zero    = {1'b0};
            bins upper_nonzero = {1'b1};
        }
    `endif

    // AMO ordering bits: aq is insn[26], rl is insn[25].
    swap_aqrl: coverpoint ins.current.insn[26:25] {
        bins aq0_rl0 = {2'b00};
        bins aq0_rl1 = {2'b01};
        bins aq1_rl0 = {2'b10};
        bins aq1_rl1 = {2'b11};
    }
    // rd is insn[11:7], rs1 insn[19:15], rs2 insn[24:20].
    swap_reg_edge: coverpoint {ins.current.insn[11:7] == 5'd0,
                               ins.current.insn[24:20] == 5'd0,
                               ins.current.insn[11:7] == ins.current.insn[19:15]} {
        bins all_distinct = {3'b000};
        bins rd_eq_rs1    = {3'b001};
        bins rs2_x0       = {3'b010};
        bins rd_x0        = {3'b100};
    }

    // ── Enable-chain (SSE) building blocks ────────────────────────────────
    senvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // Zicfiss active for U-mode requires BOTH menvcfg.SSE and senvcfg.SSE.
    // menvcfg.SSE=0 forces senvcfg.SSE read-only zero. Clearing menvcfg.SSE does not re-log
    // senvcfg, so until the next senvcfg write the trace can still show senvcfg.SSE=1; ANDing with
    // menvcfg.SSE gives the effective value. An explicit senvcfg write is logged legalized.
    u_sse_active: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                              ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1 &&
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))} {
        bins inactive_both_off = {2'b00};
        bins inactive_sen_off  = {2'b10};
        bins active            = {2'b11};
    }
    u_sse_inactive: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                                ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1 &&
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))} {
        bins both_off = {2'b00};
        bins sen_off  = {2'b10};
    }

    // ── Target page / PMA building blocks ─────────────────────────────────
    // pte.A is bit 6 and pte.D is bit 7.
    pte_ad: coverpoint ins.current.pte_d[7:6] {
        bins a0_d0 = {2'b00};
        bins a1_d0 = {2'b01};
        bins a0_d1 = {2'b10};
        bins a1_d1 = {2'b11};
    }
    `ifdef SVPBMT_SUPPORTED
        // pte.PBMT is bits [62:61]: 00 PMA, 01 NC, 10 IO. IO is non-idempotent.
        pte_pbmt: coverpoint ins.current.pte_d[62:61] {
            bins pma = {2'b00};
            bins nc  = {2'b01};
            bins io  = {2'b10};
        }
        // Without menvcfg.PBMTE a nonzero PBMT is reserved.
        menvcfg_pbmte: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte") {
            bins enabled = {1'b1};
        }
    `endif
    // Where ssp sits inside its page. A push decrements before storing, so a pointer
    // at the page base writes into the preceding page.
    ssp_page_offset: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp")[11:0] {
        bins at_page_base = {12'h000};
        bins near_base    = {[12'h001:12'h010]};
        bins mid_page     = {[12'h011:12'hFEF]};
        bins near_top     = {[12'hFF0:12'hFFF]};
    }

    // ── Non-SS accessors of an SS page ────────────────────────────────────
    ordinary_loadops: coverpoint ins.current.insn {
        wildcard bins lb  = {LB};
        wildcard bins lh  = {LH};
        wildcard bins lw  = {LW};
        wildcard bins lbu = {LBU};
        wildcard bins lhu = {LHU};
        `ifdef UDB_MXLEN_64
            wildcard bins ld  = {LD};
            wildcard bins lwu = {LWU};
        `endif
    }
    ordinary_amoops: coverpoint ins.current.insn {
        wildcard bins amoswap_w = {AMOSWAP_W};
        wildcard bins amoadd_w  = {AMOADD_W};
        wildcard bins amoor_w   = {AMOOR_W};
        `ifdef UDB_MXLEN_64
            wildcard bins amoswap_d = {AMOSWAP_D};
            wildcard bins amoadd_d  = {AMOADD_D};
        `endif
    }
    `ifdef ZICBOM_SUPPORTED
        cbo_ops: coverpoint ins.current.insn {
            wildcard bins cbo_clean = {CBO_CLEAN};
            wildcard bins cbo_flush = {CBO_FLUSH};
            wildcard bins cbo_inval = {CBO_INVAL};
        }
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cboz_ops: coverpoint ins.current.insn {
            wildcard bins cbo_zero = {CBO_ZERO};
        }
    `endif
    `ifdef ZALRSC_SUPPORTED
        lrsc_ops: coverpoint ins.current.insn {
            wildcard bins lr_w = {LR_W};
            wildcard bins sc_w = {SC_W};
            `ifdef UDB_MXLEN_64
                wildcard bins lr_d = {LR_D};
                wildcard bins sc_d = {SC_D};
            `endif
        }
    `endif
    `ifdef ZACAS_SUPPORTED
        amocas_ops: coverpoint ins.current.insn {
            wildcard bins amocas_w = {AMOCAS_W};
            `ifdef UDB_MXLEN_64
                wildcard bins amocas_d = {AMOCAS_D};
            `endif
        }
    `endif

    `ifdef ZVE32X_SUPPORTED
        // ── Vector accessors of an SS page ────────────────────────────────────
        vector_unit_load: coverpoint ins.current.insn {
            wildcard bins vle8  = {VLE8_V};
            wildcard bins vle16 = {VLE16_V};
            wildcard bins vle32 = {VLE32_V};
        }
        vector_unit_store: coverpoint ins.current.insn {
            wildcard bins vse8  = {VSE8_V};
            wildcard bins vse16 = {VSE16_V};
            wildcard bins vse32 = {VSE32_V};
        }
        vector_strided: coverpoint ins.current.insn {
            wildcard bins vlse8  = {VLSE8_V};
            wildcard bins vlse32 = {VLSE32_V};
        }
        vector_indexed: coverpoint ins.current.insn {
            wildcard bins vluxei8 = {VLUXEI8_V};
            wildcard bins vsuxei8 = {VSUXEI8_V};
        }
        // Where the access starts: on the SS page, or on the page below it (rs1[12] differs
        // because the SS page is 4 KiB-aligned at an even page number).
        access_origin: coverpoint ins.current.rs1_val[12] {
            bins on_ss_page       = {1'b0};
            bins on_adjacent_page = {1'b1};
        }
    `endif

    // A jump to the shadow stack page: the fetch there must raise an instruction access fault
    // (implicit accesses to an SS page are not permitted), not an instruction page fault.
    jalr_instr: coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }
    jalr_target_ss_page: coverpoint ((ins.current.rs1_val + ins.current.imm) & ~1) {
        `ifdef UDB_MXLEN_64
            bins ss_page = {[64'h140300000:64'h140300FFF]};
        `else
            bins ss_page = {[32'hC0300000:32'hC0300FFF]};
        `endif
    }
    // The fetch fault is recorded with the jalr, the last instruction that retired before it.
    scause_fetch_access: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code")
                         iff (ins.current.csr_wb[CSR_SEPC]) {
        bins access_fault = {INSTRUCTION_ACCESS_FAULT};
    }

    // ── Main coverpoints ──────────────────────────────────────────────────
    // Instruction behaviour (Zicfiss active)
    cp_ssp_access:                 cross priv_mode_u, csrops, ssp_csr, ssp_write_pattern {
        // The immediate CSR forms carry a 5-bit uimm, so rs1_val can never be all-ones for them.
        ignore_bins imm_cannot_be_all_ones =
            (binsof(csrops.csrrwi) || binsof(csrops.csrrsi) || binsof(csrops.csrrci)) &&
            binsof(ssp_write_pattern.all_ones);
    }
    cp_ssp_low_bits_ro_zero:       cross priv_mode_u, csr_reg_ops, ssp_csr, ssp_wr_low_bits;
    cp_sspush:                     cross priv_mode_u, ss_push_instr, ss_push_value, pte_ss_page;
    cp_sspopchk_match:             cross priv_mode_u, ss_pop_instr, sspopchk_outcome, pte_ss_page {
        // Mismatching pops trap and are counted in cp_sspopchk_mismatch.
        ignore_bins mismatch = binsof(sspopchk_outcome.mismatched);
    }
    cp_sspopchk_mismatch:          cross priv_mode_u, ss_pop_instr, sspopchk_outcome, pte_ss_page, stval_ss_fault, scause_sw_check {
        // Matching pops retire without a trap and are counted in cp_sspopchk_match.
        ignore_bins match = binsof(sspopchk_outcome.matched);
    }
    cp_sspopchk_fault_priority:    cross priv_mode_u, ss_pop_instr, ssp_fault_address;
    cp_ssrdp:                      cross priv_mode_u, ssrdp_instr, u_sse_active;
    `ifdef UDB_MXLEN_64
        cp_ssamoswap:              cross priv_mode_u, ssamoswap_instr, swap_loaded_msb, swap_rs2_upper, pte_ss_page;
    `else
        cp_ssamoswap:              cross priv_mode_u, ssamoswap_instr, swap_loaded_msb, pte_ss_page;
    `endif
    cp_ssamoswap_aqrl:             cross priv_mode_u, ssamoswap_instr, pte_ss_page, swap_aqrl;
    cp_ssamoswap_reg_edges:        cross priv_mode_u, ssamoswap_instr, pte_ss_page, swap_reg_edge;

    // Alignment
    cp_ss_address_alignment_ssp:   cross priv_mode_u, ss_push_instr, pte_ss_page, ssp_LSBs;
    cp_ss_address_alignment_pop:   cross priv_mode_u, ss_pop_instr, pte_ss_page, ssp_LSBs;
    // The misaligned atomicity granule applies only to Zaamo, Zabha and Zacas AMOs
    // (norm:pma_mag_insts), so every misaligned SSAMOSWAP faults.
    cp_ss_address_alignment_swap:  cross priv_mode_u, ssamoswap_instr, pte_ss_page, ssamoswap_adr_LSBs;

    // Page / PMA behaviour
    cp_ss_instr_target_page:       cross priv_mode_u, ss_mem_instr, pte_xwr;
    // The SS page's U bit and sstatus.MXR: a U=0 page faults in translation from U-mode, and
    // MXR has no effect on an SS instruction's access to the R=0 SS page.
    cp_ss_instr_target_page_u_mxr: cross priv_mode_u, ss_mem_instr, pte_ss_page, pte_u, sstatus_mxr;

    // A push at the base of a page writes into the preceding page; a pop reads the
    // page ssp is already on. The fault follows the page actually accessed.
    cp_ss_page_crossing:           cross priv_mode_u, ss_stack_instr, ssp_page_offset;

    // pte.A / pte.D: SSPUSH and SSAMOSWAP write and so need D; SSPOPCHK only reads.
    cp_ss_page_ad_bits:            cross priv_mode_u, ss_mem_instr, pte_ss_page, pte_ad;

    `ifdef SVPBMT_SUPPORTED
        // PBMT=IO makes the page non-idempotent, which SS instructions must reject; NC memory is
        // idempotent.
        // Known coverage gap: the SSAMOSWAP x PBMT=NC bins are not tested. An implementation may
        // override the AMO PMA of an NC page (norm:Svpbmt_impl_may_override_pmas), so the outcome
        // is implementation-defined, and no UDB parameter yet says which behavior a DUT has.
        cp_ss_non_idempotent:      cross priv_mode_u, ss_mem_instr, pte_ss_page, pte_pbmt, menvcfg_pbmte;
    `endif
    cp_ss_page_access_store:       cross priv_mode_u, ordinary_storeops, pte_ss_page;
    cp_ss_page_access_load:        cross priv_mode_u, ordinary_loadops, pte_ss_page, sstatus_mxr;
    cp_ss_page_access_amo:         cross priv_mode_u, ordinary_amoops, pte_ss_page;
    `ifdef ZICBOM_SUPPORTED
        cp_ss_page_access_cbo:     cross priv_mode_u, cbo_ops, pte_ss_page;
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cp_ss_page_access_cboz:    cross priv_mode_u, cboz_ops, pte_ss_page;
    `endif
    `ifdef ZALRSC_SUPPORTED
        cp_ss_page_access_lrsc:    cross priv_mode_u, lrsc_ops, pte_ss_page;
    `endif
    `ifdef ZACAS_SUPPORTED
        cp_ss_page_access_amocas:  cross priv_mode_u, amocas_ops, pte_ss_page;
    `endif
    cp_ss_page_fetch:              cross priv_mode_u, jalr_instr, jalr_target_ss_page, scause_fetch_access;
    `ifdef ZVE32X_SUPPORTED
        // A shadow stack page is readable by anything that only loads, and writable only by
        // SSPUSH, C.SSPUSH and SSAMOSWAP, so vector loads succeed and vector stores fault,
        // including when the access begins on the page below and runs into the SS page.
        cp_ss_vector_load:         cross priv_mode_u, vector_unit_load, pte_ss_page, sstatus_mxr;
        cp_ss_vector_store:        cross priv_mode_u, vector_unit_store, pte_ss_page;
        cp_ss_vector_strided:      cross priv_mode_u, vector_strided, pte_ss_page, access_origin;
        cp_ss_vector_indexed:      cross priv_mode_u, vector_indexed, pte_ss_page, access_origin;
    `endif

    // Enable-chain gating
    cp_ssp_csr_gating_u:           cross priv_mode_u, csrops, ssp_csr, u_sse_active;
    cp_ssamoswap_sse_gating:       cross priv_mode_u, ssamoswap_instr, u_sse_inactive;

    // Zicfiss inactive for U-mode: the MOP-encoded instructions stay inert, even with an
    // ssp that an active instruction would fault on.
    cp_ss_instr_inactive_u:        cross priv_mode_u, ss_mop_instr, u_sse_inactive, ssp_state;
    cp_ss_unused_mop_rr7_rs2: cross priv_mode_u, mop_rr7_rs2;
    cp_ss_unused_mop_rr7_rs1: cross priv_mode_u, mop_rr7_rs1;
    cp_ss_unused_mop_rr7_rd: cross priv_mode_u, mop_rr7_rd;
    cp_ss_unused_mop_r28_rs1: cross priv_mode_u, mop_r28_rs1;
    cp_ss_unused_mop_r28_rd: cross priv_mode_u, mop_r28_rd;
    `ifdef ZCMOP_SUPPORTED
        cp_ss_unused_mop_c: cross priv_mode_u, mop_c;
    `endif
    cp_ss_page_access_store_misaligned: cross priv_mode_u, ordinary_storeops, store_addr_lsb, pte_ss_page;

endgroup
`endif

`ifdef H_SUPPORTED
covergroup Zicfiss_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfiss_coverpoints.svh"

    // ── Enable-chain building blocks ──────────────────────────────────────
    senvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    henvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // Exception flavour differs by which field gates: menvcfg.SSE=0 raises
    // ILLEGAL-instruction even when V=1, while henvcfg.SSE/senvcfg.SSE gating with V=1
    // raises VIRTUAL-instruction. The inactive_men_off bin below is therefore the
    // illegal-instruction case, not a virtual-instruction one.
    // VS-mode needs menvcfg.SSE and henvcfg.SSE. menvcfg.SSE=0 forces henvcfg.SSE read-only zero,
    // which the trace does not re-log, so henvcfg.SSE is sampled as its effective value.
    vs_sse_state: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                              ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse"))} {
        bins inactive_men_off = {2'b00};
        bins inactive_hen_off = {2'b10};
        bins active           = {2'b11};
    }
    // VU-mode additionally needs senvcfg.SSE. menvcfg.SSE=0 forces both children read-only zero,
    // which the trace does not re-log, so both are sampled as their effective values.
    vu_sse_state: coverpoint {((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse")),
                              ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                               (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))} {
        bins inactive_both   = {2'b00};
        bins inactive_hen_off = {2'b01};
        bins inactive_sen_off = {2'b10};
        bins active          = {2'b11};
    }
    vu_sse_inactive: coverpoint {((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse")),
                                 ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                                  (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))} {
        bins both_off = {2'b00};
        bins hen_off  = {2'b01};
        bins sen_off  = {2'b10};
    }

    // Read-only-zero chain: what was written into bit 3, and what reads back.
    sse_bit_written: coverpoint ins.current.rs1_val[3] {
        bins wrote_zero = {1'b0};
        bins wrote_one  = {1'b1};
    }
    senvcfg_sse_readback: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "sse") {
        bins reads_zero = {1'b0};
        bins reads_one  = {1'b1};
    }
    henvcfg_sse_readback: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "henvcfg", "sse") {
        bins reads_zero = {1'b0};
        bins reads_one  = {1'b1};
    }
    envcfg_child_csr: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
        bins henvcfg = {CSR_HENVCFG};
    }
    csr_write_ops: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
        wildcard bins csrrs = {CSRRS};
    }
    // Full three-bit enable state. Which bits actually apply depends on the mode. menvcfg.SSE=0
    // forces both children read-only zero, which the trace does not re-log, so they are sampled
    // as their effective values.
    sse_chain: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                           ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1)),
                           ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse"))} {
        bins m0s0h0 = {3'b000};
        bins m1s0h0 = {3'b100};
        bins m1s0h1 = {3'b101};
        bins m1s1h0 = {3'b110};
        bins m1s1h1 = {3'b111};
        // menvcfg.SSE=0 forces both children to 0, so any state with a set child under
        // menvcfg.SSE=0 is unreachable.
        illegal_bins m0_child_set = {3'b001, 3'b010, 3'b011};
    }
    ss_all_instr: coverpoint ins.current.insn {
        wildcard bins sspush_x1     = {SSPUSH_X1};
        wildcard bins sspush_x5     = {SSPUSH_X5};
        wildcard bins sspopchk_x1   = {SSPOPCHK_X1};
        wildcard bins sspopchk_x5   = {SSPOPCHK_X5};
        wildcard bins ssrdp         = {SSRDP};
        wildcard bins ssamoswap_w   = {SSAMOSWAP_W};
        `ifdef UDB_MXLEN_64
            wildcard bins ssamoswap_d = {SSAMOSWAP_D};
        `endif
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspush_x1   = {C_SSPUSH_X1};
            wildcard bins c_sspopchk_x5 = {C_SSPOPCHK_X5};
        `endif
    }
    // Hypervisor virtual-machine load/store. HLV only loads; HSV stores.
    `ifdef H_SUPPORTED
        hlv_ops: coverpoint ins.current.insn {
            wildcard bins hlv_b = {HLV_B};
            wildcard bins hlv_h = {HLV_H};
            wildcard bins hlv_w = {HLV_W};
            `ifdef UDB_MXLEN_64
                wildcard bins hlv_d = {HLV_D};
            `endif
        }
        hsv_ops: coverpoint ins.current.insn {
            wildcard bins hsv_b = {HSV_B};
            wildcard bins hsv_h = {HSV_H};
            wildcard bins hsv_w = {HSV_W};
            `ifdef UDB_MXLEN_64
                wildcard bins hsv_d = {HSV_D};
            `endif
        }
        hstatus_hu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu") {
            bins hu_clear = {1'b0};
            bins hu_set   = {1'b1};
        }
    `endif
    // Delegation of the software-check exception (cause 18).
    medeleg_swchk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[18] {
        bins not_delegated = {1'b0};
        bins delegated     = {1'b1};
    }
    `ifdef H_SUPPORTED
        hedeleg_swchk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[18] {
            bins not_delegated = {1'b0};
            bins delegated     = {1'b1};
        }
    `endif
    // G-stage leaf encoding. xwr=010 has no shadow stack meaning at G-stage.
    g_pte_xwr: coverpoint ins.current.pte_d[3:1] {
        bins ss_encoding = {3'b010};
        bins read_write  = {3'b011};
    }

    // ── Page / G-stage building blocks ────────────────────────────────────
    // vsatp.MODE=Bare makes SS instructions fault even with V=1.
    `ifdef UDB_MXLEN_64
        vsatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vsatp", "mode")[3:0] {
            bins bare        = {4'b0000};
            bins translating = {[4'b1000:4'b1011]};
        }
        hgatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hgatp", "mode")[3:0] {
            bins bare        = {4'b0000};
            bins translating = {[4'b1000:4'b1011]};
        }
    `else
        vsatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vsatp", "mode")[0] {
            bins bare        = {1'b0};
            bins translating = {1'b1};
        }
        hgatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hgatp", "mode")[0] {
            bins bare        = {1'b0};
            bins translating = {1'b1};
        }
    `endif

    // ── Main coverpoints ──────────────────────────────────────────────────
    // ssp CSR gating — virtual-instruction flavour.
    cp_ssp_csr_gating_vs:          cross priv_mode_vs, csrops, ssp_csr, vs_sse_state;
    cp_ssp_csr_gating_vu:          cross priv_mode_vu, csrops, ssp_csr, vu_sse_state, menvcfg_sse;

    // pte.xwr=010 is reserved at VS/VU when henvcfg.SSE=0.
    cp_ss_page_enc_virt:           cross priv_mode_vs_vu, ss_mem_instr, pte_ss_page, henvcfg_sse;

    // G-stage permission and vsatp.MODE=Bare behaviour.
    cp_ss_g_stage:                 cross priv_mode_vs_vu, ss_mem_instr, hgatp_mode;
    cp_ss_vsatp_bare:              cross priv_mode_vs_vu, ss_mem_instr, vsatp_mode;

    // MOP-encoded instructions still no-op when inactive, even at V=1.
    cp_ss_instr_inactive_virt:     cross priv_mode_vu, ss_mop_instr, vu_sse_inactive;

    // Read-only-zero chain through henvcfg, and through senvcfg at V=1.
    cp_envcfg_sse_rdonly0_virt:    cross priv_mode_hs_vs, csr_write_ops, envcfg_child_csr,
                                         sse_bit_written, senvcfg_sse_readback, henvcfg_sse_readback;

    // All eight m/s/h enable combinations against every SS instruction, in every mode.
    cp_ss_enable_chain_cross:      cross priv_mode_hs_vs_vu, ss_all_instr, sse_chain;

    // pte.xwr=010 stays reserved in G-stage tables regardless of the SSE bits.
    cp_ss_g_stage_page_enc:        cross priv_mode_vs_vu, ss_mem_instr, g_pte_xwr, hgatp_mode;

    `ifdef H_SUPPORTED
        // HLV only loads, so it may read an SS page; HSV stores, so it must fault.
        cp_ss_hlv_hsv_load:        cross priv_mode_hs, hlv_ops, pte_ss_page, hstatus_hu;
        cp_ss_hlv_hsv_store:       cross priv_mode_hs, hsv_ops, pte_ss_page, hstatus_hu;

        // Software-check delegation through medeleg[18] and hedeleg[18].
        cp_ss_swcheck_delegation:  cross priv_mode_hs_vs_vu, ss_pop_instr, medeleg_swchk, hedeleg_swchk;
    `endif

    // SSAMOSWAP traps with the VIRTUAL-instruction flavour when V=1.
    cp_ssamoswap_sse_gating_vs:    cross priv_mode_vs, ssamoswap_instr, henvcfg_sse, menvcfg_sse;
    cp_ssamoswap_sse_gating_vu:    cross priv_mode_vu, ssamoswap_instr, vu_sse_inactive, menvcfg_sse;

endgroup
`endif

function void zicfiss_sample(int hart, int issue, ins_t ins);
    `ifndef EXCLUDE_SM
        Zicfiss_Sm_cg.sample(ins);
    `endif
    `ifdef S_SUPPORTED
        Zicfiss_S_cg.sample(ins);
    `endif
    `ifdef U_SUPPORTED
        Zicfiss_U_cg.sample(ins);
    `endif
    `ifdef H_SUPPORTED
        Zicfiss_H_cg.sample(ins);
    `endif
endfunction
