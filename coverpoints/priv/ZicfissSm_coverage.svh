///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — M-mode control-plane coverage
//
// Derived from ACT4-CTP Zicfiss_simplified.xlsx, sheet ZicfissSm.
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
//
// Use of Zicfiss in M-mode is not supported by the architecture. This covergroup
// therefore covers the M-mode CONTROL plane — menvcfg.SSE gating and the read-only-zero
// propagation into senvcfg/henvcfg — plus the one M-mode instruction behaviour the
// spec does define: SSAMOSWAP always faults at M.
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICFISSSM
covergroup ZicfissSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // ── Instruction building blocks ───────────────────────────────────────
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
    senvcfg_csr: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
    }
    `ifdef H_SUPPORTED
        henvcfg_csr: coverpoint ins.current.insn[31:20] {
            bins henvcfg = {CSR_HENVCFG};
        }
    `endif
    // Only the write forms can drive a read-only-zero check.
    csr_write_ops: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
        wildcard bins csrrs = {CSRRS};
    }

    // ── Enable-chain building blocks ──────────────────────────────────────
    menvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // What the test attempted to write into bit 3 (the SSE position).
    sse_bit_written: coverpoint ins.current.rs1_val[3] {
        bins wrote_zero = {1'b0};
        bins wrote_one  = {1'b1};
    }
    // What senvcfg.SSE actually reads back afterwards. With menvcfg.SSE=0 this must
    // stay zero no matter what was written.
    senvcfg_sse_readback: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "sse") {
        bins reads_zero = {1'b0};
        bins reads_one  = {1'b1};
    }
    `ifdef H_SUPPORTED
        // henvcfg is not modelled by get_csr_val, so index the raw CSR. SSE is bit 3.
        henvcfg_sse_readback: coverpoint ins.current.csr[CSR_HENVCFG][3] {
            bins reads_zero = {1'b0};
            bins reads_one  = {1'b1};
        }
    `endif

    // ── Translation-mode building blocks ──────────────────────────────────
    // SSAMOSWAP must fault at M regardless of satp.MODE, so sweep Bare vs non-Bare.
    `ifdef UDB_MXLEN_64
        satp_mode: coverpoint ins.current.csr[CSR_SATP][63:60] {
            bins bare     = {4'b0000};
            bins translating = {[4'b1000:4'b1011]};
        }
    `else
        satp_mode: coverpoint ins.current.csr[CSR_SATP][31] {
            bins bare        = {1'b0};
            bins translating = {1'b1};
        }
    `endif
    // ── Main coverpoints ──────────────────────────────────────────────────
    // SSAMOSWAP at M faults unconditionally — sweep every axis that might wrongly
    // be treated as a precondition.
    cp_ssamoswap_mmode_fault:      cross priv_mode_m, ssamoswap_instr, menvcfg_sse, satp_mode;

    // menvcfg.SSE gates ssp CSR access from S/HS.
    cp_menvcfg_sse_gating:         cross priv_mode_m_s, csrops, ssp_csr, menvcfg_sse;

    // menvcfg.SSE=0 forces senvcfg.SSE (and henvcfg.SSE) read-only zero.
    cp_envcfg_sse_rdonly0_senvcfg: cross priv_mode_m, csr_write_ops, senvcfg_csr, menvcfg_sse,
                                         sse_bit_written, senvcfg_sse_readback;
    `ifdef H_SUPPORTED
        cp_envcfg_sse_rdonly0_henvcfg: cross priv_mode_m, csr_write_ops, henvcfg_csr, menvcfg_sse,
                                             sse_bit_written, henvcfg_sse_readback;
    `endif

endgroup

function void zicfisssm_sample(int hart, int issue, ins_t ins);
    ZicfissSm_cg.sample(ins);
endfunction
