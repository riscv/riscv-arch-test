///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — S/HS-mode coverage
//
// Written: Umer Shahid umer@riscv.org 2026
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICFISSS

// ssp[2] is writable only when UXLEN or SXLEN can be 32
`ifdef UDB_UXLEN_32
    `define ZICFISS_SSP_BIT2_WRITABLE
`elsif UDB_SXLEN_32
    `define ZICFISS_SSP_BIT2_WRITABLE
`endif

covergroup ZicfissS_cg with function sample(ins_t ins);
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
    cp_ss_address_alignment_ssp_s: cross priv_mode_s, ss_push_instr, ssp_LSBs;
    cp_ss_address_alignment_pop_s: cross priv_mode_s, ss_pop_instr, ssp_LSBs;
    // The misaligned atomicity granule applies only to Zaamo, Zabha and Zacas AMOs
    // (norm:pma_mag_insts), so every misaligned SSAMOSWAP faults.
    cp_ss_address_alignment_swap_s: cross priv_mode_s, ssamoswap_instr, ssamoswap_adr_LSBs;
    cp_ss_instr_target_page_s:     cross priv_mode_s, ss_mem_instr, pte_xwr;

    `ifdef SVPBMT_SUPPORTED
        // PBMT=IO makes the page non-idempotent, which SS instructions must reject; NC memory is
        // idempotent. With PBMTE=0 a nonzero PBMT is reserved instead.
        // Known coverage gap: the SSAMOSWAP x PBMT=NC x PBMTE=1 bins are not tested. An
        // implementation may override the AMO PMA of an NC page (norm:Svpbmt_impl_may_override_pmas),
        // so the outcome is implementation-defined, and no UDB parameter yet says which behavior a
        // DUT has.
        cp_ss_non_idempotent_s:    cross priv_mode_s, ss_mem_instr, pte_pbmt, menvcfg_pbmte;
    `endif

    // The U/SUM/MXR permission check resolves before any shadow stack rule, so where
    // the two disagree the translation fault is what gets reported.
    cp_ss_page_perm_priority:      cross priv_mode_s, ss_mem_instr, pte_u, sstatus_sum, sstatus_mxr;
    cp_ss_page_perm_priority_load: cross priv_mode_s, ordinary_loadops, pte_u, sstatus_sum, sstatus_mxr;
    cp_ss_page_perm_priority_store: cross priv_mode_s, ordinary_storeops, pte_u, sstatus_sum, sstatus_mxr;

    // Set and clear senvcfg.SSE under both values of menvcfg.SSE; the signature checks that it
    // reads back 0 whenever menvcfg.SSE is 0.
    cp_senvcfg_sse_rdonly0_s:      cross priv_mode_s, senvcfg_csr, menvcfg_sse, sse_bit_write;

endgroup

function void zicfisss_sample(int hart, int issue, ins_t ins);
    ZicfissS_cg.sample(ins);
endfunction
