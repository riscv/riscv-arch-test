///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — VS/VU-mode (H-extension) coverage
//
// Derived from ACT4-CTP Zicfiss_simplified.xlsx, sheet ZicfissH.
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
//
// The virtualised half of the enable chain. Two things make V=1 different and are the
// reason this is a separate covergroup rather than more bins on ZicfissU:
//   * the same gating condition yields an ILLEGAL-instruction exception at V=0 but a
//     VIRTUAL-instruction exception at V=1;
//   * G-stage translation adds the store/AMO guest-page-fault (cause 23) flavour of the
//     SS fault-code remapping.
//
// henvcfg is not modelled by get_csr_val, so its SSE field (bit 3) is indexed directly
// off the raw CSR array.
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICFISSH
covergroup ZicfissH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // ── Instruction building blocks ───────────────────────────────────────
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
    ss_mop_instr: coverpoint ins.current.insn {
        wildcard bins sspush_x1     = {SSPUSH_X1};
        wildcard bins sspush_x5     = {SSPUSH_X5};
        wildcard bins sspopchk_x1   = {SSPOPCHK_X1};
        wildcard bins sspopchk_x5   = {SSPOPCHK_X5};
        wildcard bins ssrdp         = {SSRDP};
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspush_x1   = {C_SSPUSH_X1};
            wildcard bins c_sspopchk_x5 = {C_SSPOPCHK_X5};
        `endif
    }
    ssamoswap_instr: coverpoint ins.current.insn {
        wildcard bins ssamoswap_w = {SSAMOSWAP_W};
        `ifdef UDB_MXLEN_64
            wildcard bins ssamoswap_d = {SSAMOSWAP_D};
        `endif
    }
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
    senvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    henvcfg_sse: coverpoint ins.prev.csr[CSR_HENVCFG][3] {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // VS-mode needs menvcfg.SSE and henvcfg.SSE.
    vs_sse_state: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse"),
                              ins.prev.csr[CSR_HENVCFG][3]} {
        bins inactive_men_off = {2'b01};
        bins inactive_hen_off = {2'b10};
        bins inactive_both    = {2'b00};
        bins active           = {2'b11};
    }
    // VU-mode additionally needs senvcfg.SSE.
    vu_sse_state: coverpoint {ins.prev.csr[CSR_HENVCFG][3],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse")} {
        bins inactive_both   = {2'b00};
        bins inactive_hen_off = {2'b01};
        bins inactive_sen_off = {2'b10};
        bins active          = {2'b11};
    }
    vu_sse_inactive: coverpoint {ins.prev.csr[CSR_HENVCFG][3],
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse")} {
        bins both_off = {2'b00};
        bins hen_off  = {2'b01};
        bins sen_off  = {2'b10};
    }

    // ── Page / G-stage building blocks ────────────────────────────────────
    pte_ss_page: coverpoint ins.current.pte_d[3:1] {
        bins ss_page = {3'b010};
    }
    // vsatp.MODE=Bare makes SS instructions fault even with V=1.
    `ifdef UDB_MXLEN_64
        vsatp_mode: coverpoint ins.current.csr[CSR_VSATP][63:60] {
            bins bare        = {4'b0000};
            bins translating = {[4'b1000:4'b1011]};
        }
        hgatp_mode: coverpoint ins.current.csr[CSR_HGATP][63:60] {
            bins bare        = {4'b0000};
            bins translating = {[4'b1000:4'b1011]};
        }
    `else
        vsatp_mode: coverpoint ins.current.csr[CSR_VSATP][31] {
            bins bare        = {1'b0};
            bins translating = {1'b1};
        }
        hgatp_mode: coverpoint ins.current.csr[CSR_HGATP][31] {
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

    // SSAMOSWAP traps with the VIRTUAL-instruction flavour when V=1.
    cp_ssamoswap_sse_gating_vs:    cross priv_mode_vs, ssamoswap_instr, henvcfg_sse, menvcfg_sse;
    cp_ssamoswap_sse_gating_vu:    cross priv_mode_vu, ssamoswap_instr, vu_sse_inactive, menvcfg_sse;

endgroup

function void zicfissh_sample(int hart, int issue, ins_t ins);
    ZicfissH_cg.sample(ins);
endfunction
