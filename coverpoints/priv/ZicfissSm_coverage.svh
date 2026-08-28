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
    ss_pop_instr: coverpoint ins.current.insn {
        wildcard bins sspopchk_x1   = {SSPOPCHK_X1};
        wildcard bins sspopchk_x5   = {SSPOPCHK_X5};
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspopchk_x5 = {C_SSPOPCHK_X5};
        `endif
    }
    // MOP-encoded instructions: these revert to Zimop/Zcmop whenever Zicfiss is
    // inactive, which at M-mode is unconditional. SSAMOSWAP is AMO-encoded and traps
    // instead, so it is deliberately not in this list.
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
    // ssp alignment, used to prove an inactive instruction stays inert even when ssp
    // would otherwise fault.
    ssp_LSBs: coverpoint ins.prev.csr[CSR_SSP][2:0] {
    }
    // menvcfg.SSE x senvcfg.SSE. {0,1} is unreachable: menvcfg.SSE=0 forces
    // senvcfg.SSE read-only zero.
    sse_state: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                           (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1)} {
        bins men0_sen0 = {2'b00};
        bins men1_sen0 = {2'b10};
        bins men1_sen1 = {2'b11};
        illegal_bins men0_sen1 = {2'b01};
    }
    // pmp0cfg R is bit 0, W is bit 1. Shadow stack instructions require read-write.
    pmp0_rw: coverpoint ins.current.csr[CSR_PMPCFG0][1:0] {
        bins no_perm    = {2'b00};
        bins read_only  = {2'b01};
        bins write_only = {2'b10};
        bins read_write = {2'b11};
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

    // Shadow stack instructions require PMP read-write permission, including SSPOPCHK
    // which only reads. The denied case also proves the PMP fault outranks the
    // software-check exception a value mismatch would raise.
    cp_ss_pmp_permissions:         cross priv_mode_s, ss_mem_instr, pmp0_rw;

    // Zicfiss inactive: MOP-encoded instructions stay inert. At M-mode this is
    // unconditional; the lower-mode legs are gated by the SSE chain. ssp_LSBs proves
    // inertness holds even when ssp is misaligned.
    cp_ss_instr_inactive:          cross priv_mode_m_s, ss_mop_instr, sse_state, ssp_LSBs;

    // menvcfg.SSE=0 forces senvcfg.SSE (and henvcfg.SSE) read-only zero.
    cp_envcfg_sse_rdonly0_senvcfg: cross priv_mode_m, csr_write_ops, senvcfg_csr, menvcfg_sse,
                                         sse_bit_written, senvcfg_sse_readback {
        // menvcfg.SSE=0 forces senvcfg.SSE read-only zero, so a read-back of 1 is
        // architecturally impossible in that half of the cross.
        ignore_bins rdonly0_cannot_read_one =
            binsof(menvcfg_sse.sse_off) && binsof(senvcfg_sse_readback.reads_one);
    }
    `ifdef H_SUPPORTED
        cp_envcfg_sse_rdonly0_henvcfg: cross priv_mode_m, csr_write_ops, henvcfg_csr, menvcfg_sse,
                                             sse_bit_written, henvcfg_sse_readback;
    `endif

endgroup

function void zicfisssm_sample(int hart, int issue, ins_t ins);
    ZicfissSm_cg.sample(ins);
endfunction
