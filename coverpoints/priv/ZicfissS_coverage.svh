///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — S/HS-mode coverage
//
// Testplan: the ZicfissS sheet linked from docs/ctp/src/privmisc23.adoc.
//
// Written: Umer Shahid umer@riscv.org 2026
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
//
// Two jobs here:
//  1. S-specific gating — menvcfg.SSE alone gates S/HS; senvcfg.SSE must NOT. The
//     senvcfg sweeps in cp_ssp_csr_gating_s and cp_ssamoswap_sse_gating_s prove the negative.
//  2. The instruction-behaviour coverpoints re-crossed against priv_mode_s, so the
//     S-mode re-run of the ZicfissU generators has somewhere to land. The building
//     blocks are duplicated from ZicfissU_coverage.svh by design — this mirrors how
//     ExceptionsU/ExceptionsS are structured.
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

    // ── Instruction building blocks ───────────────────────────────────────
    ss_push_instr: coverpoint ins.current.insn {
        wildcard bins sspush_x1   = {SSPUSH_X1};
        wildcard bins sspush_x5   = {SSPUSH_X5};
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspush_x1 = {C_SSPUSH_X1};
        `endif
    }
    ss_pop_instr: coverpoint ins.current.insn {
        wildcard bins sspopchk_x1   = {SSPOPCHK_X1};
        wildcard bins sspopchk_x5   = {SSPOPCHK_X5};
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspopchk_x5 = {C_SSPOPCHK_X5};
        `endif
    }
    ssrdp_instr: coverpoint ins.current.insn {
        wildcard bins ssrdp = {SSRDP};
    }
    ssamoswap_instr: coverpoint ins.current.insn {
        wildcard bins ssamoswap_w = {SSAMOSWAP_W};
        `ifdef UDB_MXLEN_64
            wildcard bins ssamoswap_d = {SSAMOSWAP_D};
        `endif
    }
    ss_mem_instr: coverpoint ins.current.insn {
        wildcard bins sspush_x1     = {SSPUSH_X1};
        wildcard bins sspush_x5     = {SSPUSH_X5};
        wildcard bins sspopchk_x1   = {SSPOPCHK_X1};
        wildcard bins sspopchk_x5   = {SSPOPCHK_X5};
        wildcard bins ssamoswap_w   = {SSAMOSWAP_W};
        `ifdef UDB_MXLEN_64
            wildcard bins ssamoswap_d = {SSAMOSWAP_D};
        `endif
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspush_x1   = {C_SSPUSH_X1};
            wildcard bins c_sspopchk_x5 = {C_SSPOPCHK_X5};
        `endif
    }

    // ── ssp CSR building blocks ───────────────────────────────────────────
    csrops: coverpoint ins.current.insn {
        wildcard bins csrrw  = {CSRRW};
        wildcard bins csrrs  = {CSRRS};
        wildcard bins csrrc  = {CSRRC};
        wildcard bins csrrwi = {CSRRWI};
        wildcard bins csrrsi = {CSRRSI};
        wildcard bins csrrci = {CSRRCI};
    }
    ssp_csr: coverpoint ins.current.insn[31:20] {
        bins ssp = {CSR_SSP};
    }

    // ── Enable-chain building blocks ──────────────────────────────────────
    menvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
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
    // pte.xwr of the PTE the walk ended on. 000 at the last level is a pointer where a
    // leaf is required and 110 is reserved, so both fail the walk itself.
    pte_xwr: coverpoint ins.current.pte_d[3:1] iff (ins.current.pte_d[0]) {
        bins non_leaf        = {3'b000};
        bins read_only       = {3'b001};
        bins ss_page         = {3'b010};
        bins read_write      = {3'b011};
        bins exec_only       = {3'b100};
        bins exec_read       = {3'b101};
        bins rsvd_wx         = {3'b110};
        bins read_write_exec = {3'b111};
    }
    pte_ss_page: coverpoint ins.current.pte_d[3:1] {
        bins ss_page = {3'b010};
    }
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
    // ssp[1:0] are read-only zero, and so is ssp[2] unless UXLEN or SXLEN can be 32.
    ssp_LSBs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp")[2:0] {
        bins aligned_8 = {3'b000};
        `ifdef ZICFISS_SSP_BIT2_WRITABLE
            bins aligned_4 = {3'b100};
        `endif
    }
    ssamoswap_adr_LSBs: coverpoint ins.current.rs1_val[2:0] {
        // auto fills 000 through 111
    }
    sspopchk_outcome: coverpoint ins.current.trap {
        bins matched    = {1'b0};
        bins mismatched = {1'b1};
    }
    ordinary_loadops: coverpoint ins.current.insn {
        wildcard bins lb  = {LB};
        wildcard bins lh  = {LH};
        wildcard bins lw  = {LW};
        `ifdef UDB_MXLEN_64
            wildcard bins ld = {LD};
        `endif
    }
    ordinary_storeops: coverpoint ins.current.insn {
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
        `endif
    }

    // U/SUM/MXR are part of address translation and resolve before any Zicfiss rule.
    // sstatus.SUM is bit 18, sstatus.MXR is bit 19.
    pte_u: coverpoint ins.current.pte_d[4] {
        bins supervisor = {1'b0};
        bins user       = {1'b1};
    }
    sstatus_sum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum") {
        bins sum_clear = {1'b0};
        bins sum_set   = {1'b1};
    }
    sstatus_mxr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
        bins mxr_clear = {1'b0};
        bins mxr_set   = {1'b1};
    }
    // The SSE bit alone set (csrrs) or cleared (csrrc): funct3 is insn[14:12] and SSE is
    // bit 3 of rs1. Setting or clearing only SSE leaves every other field of the CSR alone.
    sse_bit_write: coverpoint {ins.current.insn[14:12], ins.current.rs1_val[3]} {
        bins set_sse   = {4'b0101};
        bins clear_sse = {4'b0111};
    }
    senvcfg_csr: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
    }

    // SSPOPCHK's base is implicitly ssp, so the faulting address is ssp itself.
    // ssp pointed at an unmapped VA so the pop's load faults. The memory fault must
    // outrank the software-check exception that the value mismatch would otherwise raise.
    ssp_fault_address: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        `ifdef UDB_MXLEN_64
            bins unmapped = {64'h140400000};
        `else
            bins unmapped = {32'hC0400000};
        `endif
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

    // S-mode re-run of the ZicfissU instruction coverpoints.
    // On a software-check exception stval reports shadow stack fault (code 3), or 0 if the
    // implementation provides no information.
    // Guarded on the trap being taken by this instruction, since the CSR array is persistent.
    stval_ss_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval")
                    iff (ins.current.csr_wb[CSR_SEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sepc", "sepc") == ins.current.pc_rdata)) {
        `ifdef UDB_REPORT_CAUSE_IN_STVAL_ON_SHADOW_STACK_SOFTWARE_CHECK
            bins ss_fault = {3};
        `else
            bins no_info = {0};
        `endif
    }
    // The trap this instruction took is a software-check exception, so an unrelated memory fault
    // on a pop cannot fill the mismatch bins.
    scause_sw_check: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code")
                     iff (ins.current.csr_wb[CSR_SEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sepc", "sepc") == ins.current.pc_rdata)) {
        bins sw_check = {SOFTWARE_CHECK};
    }

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
