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
        // SSAMOSWAP at M with MPRV=1 and MPV=1, effective mode VS (MPP=S) or VU (MPP=U), as
        // {MPRV, MPP, MPV, vsatp.MODE != Bare, henvcfg.SSE, rs1 on the SS page, on the read-only
        // G-stage window, on the user alias}. The windows are those of the H group.
        mprv_virt_access: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv")[0],
                                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0],
                                      `ifdef UDB_MXLEN_64
                                          get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv")[0],
                                          (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[3:0] != 0),
                                      `else
                                          get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv")[0],
                                          (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[0] != 0),
                                      `endif
                                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse")[0],
                                      `ifdef UDB_MXLEN_64
                                          (ins.current.rs1_val[63:12] == 52'h140300),
                                          (ins.current.rs1_val[63:12] == 52'h140331),
                                          (ins.current.rs1_val[63:12] == 52'h140328)} {
                                      `else
                                          (ins.current.rs1_val[31:12] == 20'hC0300),
                                          (ins.current.rs1_val[31:12] == 20'hC0331),
                                          (ins.current.rs1_val[31:12] == 20'hC0328)} {
                                      `endif
            bins s_ss_page        = {9'b1_01_1_1_1_100};
            bins s_henvcfg_sse0   = {9'b1_01_1_1_0_100};
            bins s_g_read_only    = {9'b1_01_1_1_1_010};
            bins s_vsatp_bare     = {9'b1_01_1_0_1_000};
            bins u_user_page      = {9'b1_00_1_1_1_001};
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
        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {}
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
    // Zicfiss_H_cg (cp_envcfg_sse_rdonly0_virt), and so does the HS-mode counterpart of the
    // henvcfg leg (cp_henvcfg_sse_rdonly0_hs).
    `ifdef H_SUPPORTED
        cp_envcfg_sse_rdonly0_henvcfg: cross priv_mode_m, henvcfg_csr, menvcfg_sse, sse_bit_write;
        // SSAMOSWAP with MPRV=1, MPV=1: two-stage translation with the guest's shadow stack rules.
        cp_ssamoswap_mprv_virt:        cross priv_mode_m, ssamoswap_instr, mprv_virt_access;
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
    senvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse")[0] {}
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
        menvcfg_pbmte: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte")[0] {}
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
    sstatus_sum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum")[0] {}
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
    `include "general/Zicfiss_U_coverpoints.svh"

    // ── Enable-chain (SSE) building blocks ────────────────────────────────
    senvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse")[0] {}
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
        access_origin: coverpoint ins.current.rs1_val[12] {}
    `endif

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
// The H group runs its guests under two-stage translation, with every VS-stage and G-stage variation
// mapped at its own guest virtual address (Zicfiss.py: the alias windows of the H group). A two-stage
// walk does not report which stage's leaf it ended on, so these coverpoints identify the page an
// access used by that address: ssp for SSPUSH and SSPOPCHK, rs1 for SSAMOSWAP and ordinary accesses.
covergroup Zicfiss_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/Zicfiss_coverpoints.svh"
    `include "general/Zicfiss_U_coverpoints.svh"

    // ── Address windows ───────────────────────────────────────────────────
    // The shadow stack page itself (ssp, for pushes and pops)
    ssp_ss_page: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins ss_page = {[64'h140300000:64'h140300FFF]};
        `else
            bins ss_page = {[32'hC0300000:32'hC0300FFF]};
        `endif
    }
    // The shadow stack page itself (rs1)
    rs1_ss_page: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins ss_page = {[64'h140300000:64'h140300FFF]};
        `else
            bins ss_page = {[32'hC0300000:32'hC0300FFF]};
        `endif
    }
    // The shadow stack page with each VS-stage pte.xwr (ssp, for pushes and pops)
    ssp_xwr_alias: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins xwr_000 = {[64'h140310000:64'h140310FFF]};
            bins xwr_001 = {[64'h140311000:64'h140311FFF]};
            bins xwr_010 = {[64'h140312000:64'h140312FFF]};
            bins xwr_011 = {[64'h140313000:64'h140313FFF]};
            bins xwr_100 = {[64'h140314000:64'h140314FFF]};
            bins xwr_101 = {[64'h140315000:64'h140315FFF]};
            bins xwr_110 = {[64'h140316000:64'h140316FFF]};
            bins xwr_111 = {[64'h140317000:64'h140317FFF]};
        `else
            bins xwr_000 = {[32'hC0310000:32'hC0310FFF]};
            bins xwr_001 = {[32'hC0311000:32'hC0311FFF]};
            bins xwr_010 = {[32'hC0312000:32'hC0312FFF]};
            bins xwr_011 = {[32'hC0313000:32'hC0313FFF]};
            bins xwr_100 = {[32'hC0314000:32'hC0314FFF]};
            bins xwr_101 = {[32'hC0315000:32'hC0315FFF]};
            bins xwr_110 = {[32'hC0316000:32'hC0316FFF]};
            bins xwr_111 = {[32'hC0317000:32'hC0317FFF]};
        `endif
    }
    // The shadow stack page with each VS-stage pte.xwr (rs1)
    rs1_xwr_alias: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins xwr_000 = {[64'h140310000:64'h140310FFF]};
            bins xwr_001 = {[64'h140311000:64'h140311FFF]};
            bins xwr_010 = {[64'h140312000:64'h140312FFF]};
            bins xwr_011 = {[64'h140313000:64'h140313FFF]};
            bins xwr_100 = {[64'h140314000:64'h140314FFF]};
            bins xwr_101 = {[64'h140315000:64'h140315FFF]};
            bins xwr_110 = {[64'h140316000:64'h140316FFF]};
            bins xwr_111 = {[64'h140317000:64'h140317FFF]};
        `else
            bins xwr_000 = {[32'hC0310000:32'hC0310FFF]};
            bins xwr_001 = {[32'hC0311000:32'hC0311FFF]};
            bins xwr_010 = {[32'hC0312000:32'hC0312FFF]};
            bins xwr_011 = {[32'hC0313000:32'hC0313FFF]};
            bins xwr_100 = {[32'hC0314000:32'hC0314FFF]};
            bins xwr_101 = {[32'hC0315000:32'hC0315FFF]};
            bins xwr_110 = {[32'hC0316000:32'hC0316FFF]};
            bins xwr_111 = {[32'hC0317000:32'hC0317FFF]};
        `endif
    }
    // The shadow stack page with each VS-stage pte.A/D pair (ssp, for pushes and pops)
    ssp_ad_alias: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins a0_d0 = {[64'h140320000:64'h140320FFF]};
            bins a1_d0 = {[64'h140321000:64'h140321FFF]};
            bins a0_d1 = {[64'h140322000:64'h140322FFF]};
            bins a1_d1 = {[64'h140323000:64'h140323FFF]};
        `else
            bins a0_d0 = {[32'hC0320000:32'hC0320FFF]};
            bins a1_d0 = {[32'hC0321000:32'hC0321FFF]};
            bins a0_d1 = {[32'hC0322000:32'hC0322FFF]};
            bins a1_d1 = {[32'hC0323000:32'hC0323FFF]};
        `endif
    }
    // The shadow stack page with each VS-stage pte.A/D pair (rs1)
    rs1_ad_alias: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins a0_d0 = {[64'h140320000:64'h140320FFF]};
            bins a1_d0 = {[64'h140321000:64'h140321FFF]};
            bins a0_d1 = {[64'h140322000:64'h140322FFF]};
            bins a1_d1 = {[64'h140323000:64'h140323FFF]};
        `else
            bins a0_d0 = {[32'hC0320000:32'hC0320FFF]};
            bins a1_d0 = {[32'hC0321000:32'hC0321FFF]};
            bins a0_d1 = {[32'hC0322000:32'hC0322FFF]};
            bins a1_d1 = {[32'hC0323000:32'hC0323FFF]};
        `endif
    }
    // The shadow stack page with the mode's own pte.U, and with it flipped (ssp, for pushes and pops)
    ssp_u_window: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins own_u = {[64'h140300000:64'h140300FFF]};
            bins flipped_u = {[64'h140328000:64'h140328FFF]};
        `else
            bins own_u = {[32'hC0300000:32'hC0300FFF]};
            bins flipped_u = {[32'hC0328000:32'hC0328FFF]};
        `endif
    }
    // The shadow stack page with the mode's own pte.U, and with it flipped (rs1)
    rs1_u_window: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins own_u = {[64'h140300000:64'h140300FFF]};
            bins flipped_u = {[64'h140328000:64'h140328FFF]};
        `else
            bins own_u = {[32'hC0300000:32'hC0300FFF]};
            bins flipped_u = {[32'hC0328000:32'hC0328FFF]};
        `endif
    }
    // The alias whose walk is cached before henvcfg.SSE changes
    rs1_no_fence_alias: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins no_fence = {[64'h140329000:64'h140329FFF]};
        `else
            bins no_fence = {[32'hC0329000:32'hC0329FFF]};
        `endif
    }
    // VS-stage SS pages over each G-stage leaf (ssp, for pushes and pops)
    ssp_g_alias: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins rw = {[64'h140330000:64'h140330FFF]};
            bins r = {[64'h140331000:64'h140331FFF]};
            bins x = {[64'h140332000:64'h140332FFF]};
            bins rw_no_u = {[64'h140333000:64'h140333FFF]};
            bins invalid = {[64'h140334000:64'h140334FFF]};
            bins xwr010 = {[64'h140335000:64'h140335FFF]};
        `else
            bins rw = {[32'hC0330000:32'hC0330FFF]};
            bins r = {[32'hC0331000:32'hC0331FFF]};
            bins x = {[32'hC0332000:32'hC0332FFF]};
            bins rw_no_u = {[32'hC0333000:32'hC0333FFF]};
            bins invalid = {[32'hC0334000:32'hC0334FFF]};
            bins xwr010 = {[32'hC0335000:32'hC0335FFF]};
        `endif
    }
    // VS-stage SS pages over each G-stage leaf (rs1)
    rs1_g_alias: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins rw = {[64'h140330000:64'h140330FFF]};
            bins r = {[64'h140331000:64'h140331FFF]};
            bins x = {[64'h140332000:64'h140332FFF]};
            bins rw_no_u = {[64'h140333000:64'h140333FFF]};
            bins invalid = {[64'h140334000:64'h140334FFF]};
            bins xwr010 = {[64'h140335000:64'h140335FFF]};
        `else
            bins rw = {[32'hC0330000:32'hC0330FFF]};
            bins r = {[32'hC0331000:32'hC0331FFF]};
            bins x = {[32'hC0332000:32'hC0332FFF]};
            bins rw_no_u = {[32'hC0333000:32'hC0333FFF]};
            bins invalid = {[32'hC0334000:32'hC0334FFF]};
            bins xwr010 = {[32'hC0335000:32'hC0335FFF]};
        `endif
    }
    // A VS-stage RWX page over the reserved G-stage xwr=010
    rs1_g_rwx_alias: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins g_xwr010 = {[64'h140336000:64'h140336FFF]};
        `else
            bins g_xwr010 = {[32'hC0336000:32'hC0336FFF]};
        `endif
    }
    // Store/AMO guest-page faults: on the access itself, or on the VS-stage walk's table read
    ssp_gpf_window: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins explicit = {[64'h140334000:64'h140334FFF]};
            bins implicit = {[64'h140B00000:64'h140B00FFF]};
        `else
            bins explicit = {[32'hC0334000:32'hC0334FFF]};
            bins implicit = {[32'hC0B00000:32'hC0B00FFF]};
        `endif
    }
    // Store/AMO guest-page faults for SSAMOSWAP
    rs1_gpf_window: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins explicit = {[64'h140334000:64'h140334FFF]};
            bins implicit = {[64'h140B00000:64'h140B00FFF]};
        `else
            bins explicit = {[32'hC0334000:32'hC0334FFF]};
            bins implicit = {[32'hC0B00000:32'hC0B00FFF]};
        `endif
    }
    // VS-stage PBMT over G-stage PBMT (ssp, for pushes and pops)
    ssp_pbmt_alias: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins vs_pma_g_pma = {[64'h140340000:64'h140340FFF]};
            bins vs_pma_g_nc = {[64'h140341000:64'h140341FFF]};
            bins vs_pma_g_io = {[64'h140342000:64'h140342FFF]};
            bins vs_nc_g_pma = {[64'h140343000:64'h140343FFF]};
            bins vs_nc_g_nc = {[64'h140344000:64'h140344FFF]};
            bins vs_nc_g_io = {[64'h140345000:64'h140345FFF]};
            bins vs_io_g_pma = {[64'h140346000:64'h140346FFF]};
            bins vs_io_g_nc = {[64'h140347000:64'h140347FFF]};
            bins vs_io_g_io = {[64'h140348000:64'h140348FFF]};
        `else
            bins vs_pma_g_pma = {[32'hC0340000:32'hC0340FFF]};
            bins vs_pma_g_nc = {[32'hC0341000:32'hC0341FFF]};
            bins vs_pma_g_io = {[32'hC0342000:32'hC0342FFF]};
            bins vs_nc_g_pma = {[32'hC0343000:32'hC0343FFF]};
            bins vs_nc_g_nc = {[32'hC0344000:32'hC0344FFF]};
            bins vs_nc_g_io = {[32'hC0345000:32'hC0345FFF]};
            bins vs_io_g_pma = {[32'hC0346000:32'hC0346FFF]};
            bins vs_io_g_nc = {[32'hC0347000:32'hC0347FFF]};
            bins vs_io_g_io = {[32'hC0348000:32'hC0348FFF]};
        `endif
    }
    // VS-stage PBMT over G-stage PBMT (rs1)
    rs1_pbmt_alias: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins vs_pma_g_pma = {[64'h140340000:64'h140340FFF]};
            bins vs_pma_g_nc = {[64'h140341000:64'h140341FFF]};
            bins vs_pma_g_io = {[64'h140342000:64'h140342FFF]};
            bins vs_nc_g_pma = {[64'h140343000:64'h140343FFF]};
            bins vs_nc_g_nc = {[64'h140344000:64'h140344FFF]};
            bins vs_nc_g_io = {[64'h140345000:64'h140345FFF]};
            bins vs_io_g_pma = {[64'h140346000:64'h140346FFF]};
            bins vs_io_g_nc = {[64'h140347000:64'h140347FFF]};
            bins vs_io_g_io = {[64'h140348000:64'h140348FFF]};
        `else
            bins vs_pma_g_pma = {[32'hC0340000:32'hC0340FFF]};
            bins vs_pma_g_nc = {[32'hC0341000:32'hC0341FFF]};
            bins vs_pma_g_io = {[32'hC0342000:32'hC0342FFF]};
            bins vs_nc_g_pma = {[32'hC0343000:32'hC0343FFF]};
            bins vs_nc_g_nc = {[32'hC0344000:32'hC0344FFF]};
            bins vs_nc_g_io = {[32'hC0345000:32'hC0345FFF]};
            bins vs_io_g_pma = {[32'hC0346000:32'hC0346FFF]};
            bins vs_io_g_nc = {[32'hC0347000:32'hC0347FFF]};
            bins vs_io_g_io = {[32'hC0348000:32'hC0348FFF]};
        `endif
    }
    // PBMT windows whose final memory type is not NC: SSAMOSWAP skips NC (see cp_ss_non_idempotent)
    rs1_pbmt_not_nc: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins vs_pma_g_pma = {[64'h140340000:64'h140340FFF]};
            bins vs_pma_g_io = {[64'h140342000:64'h140342FFF]};
            bins vs_io_g_pma = {[64'h140346000:64'h140346FFF]};
            bins vs_io_g_nc = {[64'h140347000:64'h140347FFF]};
            bins vs_io_g_io = {[64'h140348000:64'h140348FFF]};
        `else
            bins vs_pma_g_pma = {[32'hC0340000:32'hC0340FFF]};
            bins vs_pma_g_io = {[32'hC0342000:32'hC0342FFF]};
            bins vs_io_g_pma = {[32'hC0346000:32'hC0346FFF]};
            bins vs_io_g_nc = {[32'hC0347000:32'hC0347FFF]};
            bins vs_io_g_io = {[32'hC0348000:32'hC0348FFF]};
        `endif
    }

    // The read-only and read/write aliases, where an SS instruction raises a store/AMO page fault and access fault.
    ssp_fault_alias: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins read_only  = {[64'h140311000:64'h140311FFF]};
            bins read_write = {[64'h140313000:64'h140313FFF]};
        `else
            bins read_only  = {[32'hC0311000:32'hC0311FFF]};
            bins read_write = {[32'hC0313000:32'hC0313FFF]};
        `endif
    }

    // ── Enable-chain building blocks ──────────────────────────────────────
    henvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse")[0] {}
    // menvcfg.SSE=0 forces henvcfg.SSE read-only zero, which the trace does not re-log, so
    // henvcfg.SSE is sampled as its effective value.
    vs_sse_state: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                              ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                               (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse") == 1))} {
        bins inactive_men_off = {2'b00};
        bins inactive_hen_off = {2'b10};
        bins active           = {2'b11};
    }
    // {menvcfg.SSE, senvcfg.SSE, henvcfg.SSE}, with the children sampled as effective values under
    // menvcfg.SSE. senvcfg.SSE is the value HS-mode wrote: at V=1 it reads 0 while henvcfg.SSE=0,
    // which m1s1h0 shows is what VU-mode sees. Which bits apply depends on the mode.
    sse_chain: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                           ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1)),
                           ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse") == 1))} {
        bins m0s0h0 = {3'b000};
        bins m1s0h0 = {3'b100};
        bins m1s0h1 = {3'b101};
        bins m1s1h0 = {3'b110};
        bins m1s1h1 = {3'b111};
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
    senvcfg_csr: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
    }
    henvcfg_csr: coverpoint ins.current.insn[31:20] {
        bins henvcfg = {CSR_HENVCFG};
    }
    // csrr ssp (csrrs with rs1 = x0) and csrw ssp (csrrw with rd = x0).
    ssp_read_write: coverpoint ins.current.insn {
        wildcard bins read  = {32'b000000010001_00000_010_?????_1110011};
        wildcard bins write = {32'b000000010001_?????_001_00000_1110011};
    }

    // ── Outcome building blocks ───────────────────────────────────────────
    pop_matched: coverpoint ins.current.trap {
        type_option.weight = 0;
        bins matched = {1'b0};
    }
    pop_mismatched: coverpoint ins.current.trap {
        type_option.weight = 0;
        bins mismatched = {1'b1};
    }
    // A software-check exception delegated to VS-mode (hedeleg[18] = 1): vscause and vstval.
    vs_sw_check_exc: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vscause", "code")
                     iff (ins.current.csr_wb[CSR_VSCAUSE]) {
        bins software_check = {SOFTWARE_CHECK};
    }
    vstval_ss_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vstval", "vstval")
                     iff (ins.current.csr_wb[CSR_VSCAUSE]) {
        `ifdef UDB_REPORT_CAUSE_IN_VSTVAL_ON_SHADOW_STACK_SOFTWARE_CHECK
            bins ss_fault = {3};
        `else
            bins no_info = {0};
        `endif
    }
    // An SS instruction's access fault and page fault delegated to VS-mode keep the store/AMO flavour.
    vs_ss_fault_exc: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vscause", "code")
                     iff (ins.current.csr_wb[CSR_VSCAUSE]) {
        bins store_access_fault = {STORE_AMO_ACCESS_FAULT};
        bins store_page_fault   = {STORE_AMO_PAGE_FAULT};
    }

    // ── Hypervisor control building blocks ────────────────────────────────
    medeleg_swchk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[18] {
        bins delegated = {1};
    }
    hedeleg_swchk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[18] {}
    // hedeleg[15] and hedeleg[7]: store/AMO page and access faults, set and cleared together.
    hedeleg_ss_faults: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[15],
                                   get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[7]} {
        bins not_delegated = {2'b00};
        bins delegated     = {2'b11};
    }
    hstatus_spvp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp")[0] {}
    hstatus_hu1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu")[0] {
        bins set = {1};
    }
    hstatus_hu0: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu")[0] {
        bins clear = {0};
    }
    // vsstatus is written only from HS-mode in these tests, so the trace logs it under its own name.
    vsstatus_sum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sum")[0] {}
    vsstatus_mxr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr")[0] {}
    `ifdef UDB_MXLEN_64
        vsatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[3:0] {
            bins bare = {4'b0000};
        }
        hgatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")[3:0] {
            bins bare        = {4'b0000};
            bins translating = {[4'b1000:4'b1011]};
        }
    `else
        vsatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[0] {
            bins bare = {1'b0};
        }
        hgatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")[0] {
            bins bare        = {1'b0};
            bins translating = {1'b1};
        }
    `endif
    `ifdef SVPBMT_SUPPORTED
        // {menvcfg.PBMTE, henvcfg.PBMTE}: henvcfg.PBMTE is cleared before menvcfg.PBMTE, so the trace
        // shows the read-only-zero value.
        pbmte_state: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte")[0],
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pbmte")[0]} {
            bins both    = {2'b11};
            bins men     = {2'b10};
            bins neither = {2'b00};
        }
        pbmte_both: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte")[0],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pbmte")[0]} {
            bins both = {2'b11};
        }
    `endif

    // ── Access building blocks ────────────────────────────────────────────
    // An ordinary load, store and fetch, at the base of a window.
    ordinary_ls_fetch: coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        `ifdef UDB_MXLEN_64
            wildcard bins ld = {LD};
        `endif
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    sspush_x1_instr: coverpoint ins.current.insn {
        wildcard bins sspush_x1 = {SSPUSH_X1};
    }
    lw_instr: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    sw_instr: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }
    hlv_ops: coverpoint ins.current.insn {
        wildcard bins hlv_b   = {HLV_B};
        wildcard bins hlv_bu  = {HLV_BU};
        wildcard bins hlv_h   = {HLV_H};
        wildcard bins hlv_hu  = {HLV_HU};
        wildcard bins hlv_w   = {HLV_W};
        `ifdef UDB_MXLEN_64
            wildcard bins hlv_wu = {HLV_WU};
            wildcard bins hlv_d  = {HLV_D};
        `endif
        wildcard bins hlvx_hu = {HLVX_HU};
        wildcard bins hlvx_wu = {HLVX_WU};
    }
    hsv_ops: coverpoint ins.current.insn {
        wildcard bins hsv_b = {HSV_B};
        wildcard bins hsv_h = {HSV_H};
        wildcard bins hsv_w = {HSV_W};
        `ifdef UDB_MXLEN_64
            wildcard bins hsv_d = {HSV_D};
        `endif
    }

    // ── U-group coverpoints re-run in VS-mode and VU-mode ─────────────────
    cp_ssp_access:                 cross priv_mode_vs_vu, csrops, ssp_csr, ssp_write_pattern {
        // The immediate CSR forms carry a 5-bit uimm, so rs1_val can never be all-ones for them.
        ignore_bins imm_cannot_be_all_ones =
            (binsof(csrops.csrrwi) || binsof(csrops.csrrsi) || binsof(csrops.csrrci)) &&
            binsof(ssp_write_pattern.all_ones);
    }
    cp_ssp_low_bits_ro_zero:       cross priv_mode_vs_vu, csr_reg_ops, ssp_csr, ssp_wr_low_bits;
    cp_sspush:                     cross priv_mode_vs_vu, ss_push_instr, ss_push_value, ssp_ss_page;
    cp_sspopchk_match:             cross priv_mode_vs_vu, ss_pop_instr, pop_matched, ssp_ss_page;
    cp_sspopchk_mismatch:          cross priv_mode_vs_vu, ss_pop_instr, pop_mismatched, ssp_ss_page, stval_ss_fault, scause_sw_check;
    cp_sspopchk_fault_priority:    cross priv_mode_vs_vu, ss_pop_instr, ssp_fault_address;
    cp_ssrdp:                      cross priv_mode_vs_vu, ssrdp_instr, ssp_ss_page;
    `ifdef UDB_MXLEN_64
        cp_ssamoswap:              cross priv_mode_vs_vu, ssamoswap_instr, swap_loaded_msb, swap_rs2_upper, rs1_ss_page;
    `else
        cp_ssamoswap:              cross priv_mode_vs_vu, ssamoswap_instr, swap_loaded_msb, rs1_ss_page;
    `endif
    cp_ssamoswap_aqrl:             cross priv_mode_vs_vu, ssamoswap_instr, rs1_ss_page, swap_aqrl;
    cp_ssamoswap_reg_edges:        cross priv_mode_vs_vu, ssamoswap_instr, rs1_ss_page, swap_reg_edge;
    cp_ss_address_alignment_ssp:   cross priv_mode_vs_vu, ss_push_instr, ssp_ss_page, ssp_LSBs;
    cp_ss_address_alignment_pop:   cross priv_mode_vs_vu, ss_pop_instr, ssp_ss_page, ssp_LSBs;
    cp_ss_address_alignment_swap:  cross priv_mode_vs_vu, ssamoswap_instr, rs1_ss_page, ssamoswap_adr_LSBs;
    cp_ss_page_crossing:           cross priv_mode_vs_vu, ss_stack_instr, ssp_page_offset;
    cp_ss_page_access_store:       cross priv_mode_vs_vu, ordinary_storeops, rs1_ss_page;
    cp_ss_page_access_load:        cross priv_mode_vs_vu, ordinary_loadops, rs1_ss_page, vsstatus_mxr;
    cp_ss_page_access_amo:         cross priv_mode_vs_vu, ordinary_amoops, rs1_ss_page;
    `ifdef ZICBOM_SUPPORTED
        cp_ss_page_access_cbo:     cross priv_mode_vs_vu, cbo_ops, rs1_ss_page;
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cp_ss_page_access_cboz:    cross priv_mode_vs_vu, cboz_ops, rs1_ss_page;
    `endif
    `ifdef ZALRSC_SUPPORTED
        cp_ss_page_access_lrsc:    cross priv_mode_vs_vu, lrsc_ops, rs1_ss_page;
    `endif
    `ifdef ZACAS_SUPPORTED
        cp_ss_page_access_amocas:  cross priv_mode_vs_vu, amocas_ops, rs1_ss_page;
    `endif
    cp_ss_page_fetch:              cross priv_mode_vs_vu, jalr_instr, jalr_target_ss_page, scause_fetch_access;
    cp_ss_page_access_store_misaligned: cross priv_mode_vs_vu, ordinary_storeops, store_addr_lsb, rs1_ss_page;

    // ── Enable chain ──────────────────────────────────────────────────────
    // ssp gating: menvcfg.SSE=0 raises an illegal-instruction exception even at V=1; henvcfg.SSE=0
    // (VS, VU) and senvcfg.SSE=0 (VU) raise virtual-instruction exceptions.
    cp_ssp_csr_gating_vs:          cross priv_mode_vs, csrops, ssp_csr, sse_chain;
    cp_ssp_csr_gating_vu:          cross priv_mode_vu, csrops, ssp_csr, sse_chain;
    cp_ssamoswap_sse_gating_vs:    cross priv_mode_vs, ssamoswap_instr, sse_chain;
    cp_ssamoswap_sse_gating_vu:    cross priv_mode_vu, ssamoswap_instr, sse_chain;
    // Every SS instruction under every reachable enable state, in HS, VS and VU.
    cp_ss_enable_chain_cross:      cross priv_mode_hs_vs_vu, ss_all_instr, sse_chain;
    // henvcfg.SSE=0 makes senvcfg.SSE read-only zero at V=1.
    cp_envcfg_sse_rdonly0_virt:    cross priv_mode_vs, senvcfg_csr, sse_bit_write, henvcfg_sse;
    // Set and clear henvcfg.SSE from HS-mode under both values of menvcfg.SSE; the signature
    // checks that it reads back 0 whenever menvcfg.SSE is 0.
    cp_henvcfg_sse_rdonly0_hs:     cross priv_mode_hs, henvcfg_csr, menvcfg_sse, sse_bit_write;
    // There is one ssp CSR; V does not switch it.
    cp_ssp_shared:                 cross priv_mode_hs_vs_vu, ssp_read_write;

    // ── VS-stage pages ────────────────────────────────────────────────────
    // pte.xwr=010 is an SS page only while menvcfg.SSE and henvcfg.SSE are 1; else it is reserved.
    cp_ss_page_enc_virt:           cross priv_mode_vs_vu, ordinary_ls_fetch, rs1_ss_page, vs_sse_state;
    // A change of henvcfg.SSE takes effect without an HFENCE.
    cp_ss_sse_change_no_fence:     cross priv_mode_vs, lw_instr, rs1_no_fence_alias, henvcfg_sse;
    cp_ss_instr_target_page:       cross priv_mode_vs_vu, ss_stack_instr, ssp_xwr_alias;
    cp_ss_instr_target_page_swap:  cross priv_mode_vs_vu, ssamoswap_instr, rs1_xwr_alias;
    cp_ss_page_ad_bits:            cross priv_mode_vs_vu, ss_stack_instr, ssp_ad_alias;
    cp_ss_page_ad_bits_swap:       cross priv_mode_vs_vu, ssamoswap_instr, rs1_ad_alias;
    // pte.U, vsstatus.SUM and vsstatus.MXR, on the SS page and on an alias with pte.U flipped.
    cp_ss_page_perm_priority:      cross priv_mode_vs_vu, ss_stack_instr, ssp_u_window, vsstatus_sum, vsstatus_mxr;
    cp_ss_page_perm_priority_swap: cross priv_mode_vs_vu, ssamoswap_instr, rs1_u_window, vsstatus_sum, vsstatus_mxr;
    cp_ss_page_perm_priority_load: cross priv_mode_vs_vu, lw_instr, rs1_u_window, vsstatus_sum, vsstatus_mxr;
    cp_ss_page_perm_priority_store: cross priv_mode_vs_vu, sw_instr, rs1_u_window, vsstatus_sum, vsstatus_mxr;

    // ── G-stage ───────────────────────────────────────────────────────────
    // An SS instruction needs a G-stage leaf with R, W and U; else a store/AMO guest-page fault.
    cp_ss_g_stage:                 cross priv_mode_vs_vu, ss_stack_instr, ssp_g_alias;
    cp_ss_g_stage_swap:            cross priv_mode_vs_vu, ssamoswap_instr, rs1_g_alias;
    // G-stage xwr=010 stays reserved for ordinary accesses too, whatever henvcfg.SSE is.
    cp_ss_g_stage_page_enc:        cross priv_mode_vs_vu, ordinary_ls_fetch, rs1_g_rwx_alias, henvcfg_sse;
    // htval and htinst of the explicit and implicit (VS-stage table read) guest-page faults.
    cp_ss_gpf_tval:                cross priv_mode_vs_vu, ss_stack_instr, ssp_gpf_window;
    cp_ss_gpf_tval_swap:           cross priv_mode_vs_vu, ssamoswap_instr, rs1_gpf_window;
    // vsatp.MODE=Bare: a store/AMO access fault, over a translating or Bare G-stage.
    cp_ss_vsatp_bare:              cross priv_mode_vs_vu, ss_mem_instr, vsatp_bare, hgatp_mode;
    `ifdef SVPBMT_SUPPORTED
        // The final memory type is the VS-stage PBMT if nonzero, else the G-stage PBMT if nonzero,
        // else the PMA; SS instructions fault where it is IO.
        cp_ss_non_idempotent_virt:      cross priv_mode_vs, ss_stack_instr, ssp_pbmt_alias, pbmte_both;
        cp_ss_non_idempotent_virt_swap: cross priv_mode_vs, ssamoswap_instr, rs1_pbmt_not_nc, pbmte_both;
        cp_ss_non_idempotent_virt_vu:   cross priv_mode_vu, ss_push_instr, ssp_pbmt_alias, pbmte_both;
        // With henvcfg.PBMTE=0 a nonzero VS-stage PBMT is reserved; with menvcfg.PBMTE=0 so is a
        // nonzero G-stage PBMT.
        cp_ss_non_idempotent_virt_pbmte: cross priv_mode_vs, sspush_x1_instr, ssp_pbmt_alias, pbmte_state;
    `endif

    // ── HLV, HLVX and HSV ─────────────────────────────────────────────────
    // HLV may read an SS page, HLVX needs execute permission, and HSV may not write it.
    cp_ss_hlv_hsv_load:            cross priv_mode_hs, hlv_ops, rs1_ss_page, hstatus_spvp, henvcfg_sse;
    cp_ss_hlv_hsv_store:           cross priv_mode_hs, hsv_ops, rs1_ss_page, hstatus_spvp, henvcfg_sse;
    cp_ss_hlv_hsv_u_load:          cross priv_mode_u, hlv_ops, rs1_ss_page, hstatus_hu1, henvcfg_sse;
    cp_ss_hlv_hsv_u_store:         cross priv_mode_u, hsv_ops, rs1_ss_page, hstatus_hu1, henvcfg_sse;
    cp_ss_hlv_hsv_hu0_load:        cross priv_mode_u, hlv_ops, hstatus_hu0;
    cp_ss_hlv_hsv_hu0_store:       cross priv_mode_u, hsv_ops, hstatus_hu0;

    // ── Delegation to VS-mode ─────────────────────────────────────────────
    cp_sspopchk_mismatch_virt:     cross priv_mode_vs_vu, ss_pop_instr, pop_mismatched, medeleg_swchk, hedeleg_swchk;
    cp_sspopchk_mismatch_vs:       cross priv_mode_vs_vu, ss_pop_instr, vs_sw_check_exc, vstval_ss_fault;
    cp_ss_fault_delegation:        cross priv_mode_vs_vu, ss_push_instr, ssp_fault_alias, hedeleg_ss_faults;
    cp_ss_fault_delegation_vs:     cross priv_mode_vs_vu, ss_push_instr, vs_ss_fault_exc;

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
