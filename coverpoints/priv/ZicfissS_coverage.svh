///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — S/HS-mode coverage
//
// Derived from ACT4-CTP Zicfiss_simplified.xlsx, sheet ZicfissS.
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
//
// Two jobs here:
//  1. S-specific gating — menvcfg.SSE alone gates S/HS; senvcfg.SSE must NOT. The
//     senvcfg sweep in cp_ssp_csr_gating_s is the only place that proves the negative.
//  2. The instruction-behaviour coverpoints re-crossed against priv_mode_s, so the
//     S-mode re-run of the ZicfissU generators has somewhere to land. The building
//     blocks are duplicated from ZicfissU_coverage.svh by design — this mirrors how
//     ExceptionsU/ExceptionsS are structured.
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICFISSS
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
    // menvcfg.SSE=0 forces senvcfg.SSE read-only zero, so {menvcfg=0, senvcfg=1} is
    // architecturally unreachable.
    s_sse_state: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                             (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1)} {
        bins men0_sen0 = {2'b00};
        bins men1_sen0 = {2'b10};
        bins men1_sen1 = {2'b11};
        illegal_bins men0_sen1 = {2'b01};
    }

    // ── Page / alignment building blocks ──────────────────────────────────
    pte_xwr: coverpoint ins.current.pte_d[3:1] {
        bins ss_page    = {3'b010};
        bins read_only  = {3'b001};
        bins read_write = {3'b011};
        bins exec_read  = {3'b101};
        bins exec_only  = {3'b100};
    }
    pte_ss_page: coverpoint ins.current.pte_d[3:1] {
        bins ss_page = {3'b010};
    }
    // pte_d is not carried by the Sail->RVVI converter; use the address instead.
    ss_target_page: coverpoint ins.prev.csr[CSR_SSP][13:12] {
        bins ss_page = {2'd0};
        bins rw_page = {2'd1};
        bins ro_page = {2'd2};
    }
    ssp_LSBs: coverpoint ins.prev.csr[CSR_SSP][2:0] {
        // auto fills 000 through 111
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
    sstatus_sum: coverpoint ins.prev.csr[CSR_SSTATUS][18] {
        bins sum_clear = {1'b0};
        bins sum_set   = {1'b1};
    }
    sstatus_mxr: coverpoint ins.prev.csr[CSR_SSTATUS][19] {
        bins mxr_clear = {1'b0};
        bins mxr_set   = {1'b1};
    }
    // What was written into senvcfg bit 3, and what it reads back as.
    sse_bit_written: coverpoint ins.current.rs1_val[3] {
        bins wrote_zero = {1'b0};
        bins wrote_one  = {1'b1};
    }
    senvcfg_sse_readback: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "sse") {
        bins reads_zero = {1'b0};
        bins reads_one  = {1'b1};
    }
    senvcfg_csr: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
    }
    csr_write_ops: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
        wildcard bins csrrs = {CSRRS};
    }

    // SSPOPCHK's base is implicitly ssp, so the faulting address is ssp itself.
    // ssp pointed at an unmapped VA so the pop's load faults. The memory fault must
    // outrank the software-check exception that the value mismatch would otherwise raise.
    ssp_fault_address: coverpoint ins.prev.csr[CSR_SSP] {
        `ifdef UDB_MXLEN_64
            bins unmapped = {64'h140400000};
        `else
            bins unmapped = {32'hC0400000};
        `endif
    }

    // ── Main coverpoints ──────────────────────────────────────────────────
    // S-specific gating: menvcfg.SSE gates, senvcfg.SSE must not.
    cp_ssp_csr_gating_s:           cross priv_mode_s, csrops, ssp_csr, s_sse_state;

    // SS page encoding is recognised only when menvcfg.SSE=1.
    cp_ss_page_enc:                cross priv_mode_s, ss_mem_instr, pte_ss_page, menvcfg_sse;
    cp_ss_page_enc_load:           cross priv_mode_s, ordinary_loadops, pte_ss_page, menvcfg_sse;
    cp_ss_page_enc_store:          cross priv_mode_s, ordinary_storeops, pte_ss_page, menvcfg_sse;

    // S-mode re-run of the ZicfissU instruction coverpoints.
    cp_sspush_s:                   cross priv_mode_s, ss_push_instr, pte_ss_page;
    cp_sspopchk_match_s:           cross priv_mode_s, ss_pop_instr, sspopchk_outcome, pte_ss_page {
        ignore_bins mismatch = binsof(sspopchk_outcome.mismatched);
    }
    cp_sspopchk_mismatch_s:        cross priv_mode_s, ss_pop_instr, sspopchk_outcome, pte_ss_page {
        ignore_bins match = binsof(sspopchk_outcome.matched);
    }
    cp_sspopchk_fault_priority_s:  cross priv_mode_s, ss_pop_instr, ssp_fault_address;
    cp_ssrdp_s:                    cross priv_mode_s, ssrdp_instr;
    cp_ssamoswap_s:                cross priv_mode_s, ssamoswap_instr, pte_ss_page;
    cp_ss_address_alignment_ssp_s: cross priv_mode_s, ss_push_instr, ssp_LSBs;
    cp_ss_address_alignment_pop_s: cross priv_mode_s, ss_pop_instr, ssp_LSBs;
    cp_ss_address_alignment_swap_s: cross priv_mode_s, ssamoswap_instr, ssamoswap_adr_LSBs;
    cp_ss_instr_target_page_s:     cross priv_mode_s, ss_mem_instr, ss_target_page;

    // The U/SUM/MXR permission check resolves before any shadow stack rule, so where
    // the two disagree the translation fault is what gets reported.
    cp_ss_page_perm_priority:      cross priv_mode_s, ss_mem_instr, pte_u, sstatus_sum, sstatus_mxr;
    cp_ss_page_perm_priority_load: cross priv_mode_s, ordinary_loadops, pte_u, sstatus_sum, sstatus_mxr;

    // senvcfg.SSE reads back 0 from S-mode whenever menvcfg.SSE is 0.
    cp_senvcfg_sse_rdonly0_s:      cross priv_mode_s, csr_write_ops, senvcfg_csr, menvcfg_sse,
                                         sse_bit_written, senvcfg_sse_readback {
        // menvcfg.SSE=0 forces senvcfg.SSE read-only zero, so a read-back of 1 is
        // architecturally impossible in that half of the cross.
        ignore_bins rdonly0_cannot_read_one =
            binsof(menvcfg_sse.sse_off) && binsof(senvcfg_sse_readback.reads_one);
    }

endgroup

function void zicfisss_sample(int hart, int issue, ins_t ins);
    ZicfissS_cg.sample(ins);
endfunction
