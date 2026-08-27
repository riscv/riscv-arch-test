///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — U-mode coverage
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICFISSU
covergroup ZicfissU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // ── Instruction building blocks ───────────────────────────────────────
    // SSPUSH/SSPOPCHK are architecturally defined only for x1 and x5.
    // The compressed forms exist only when Zcmop is implemented.
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
    // Every SS instruction that accesses memory — used for page/fault crosses.
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
    // The MOP-encoded subset only — these revert to Zimop/Zcmop when Zicfiss is
    // inactive. SSAMOSWAP is deliberately NOT in this list: it is AMO-encoded and
    // traps instead of no-opping (see cp_ssamoswap_sse_gating).
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

    // ── ssp CSR access building blocks ────────────────────────────────────
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
    ssp_write_pattern: coverpoint ins.current.rs1_val {
        bins all_zeros = {'0};
        bins all_ones  = {'1};
    }
    // ssp[1:0] are read-only zero; sweep what the test tried to write there.
    ssp_wr_low_bits: coverpoint ins.current.rs1_val[1:0] {
        // auto fills 00 through 11
    }
    // ssp[1:0] as actually read back — must always be zero.
    ssp_rd_low_bits: coverpoint ins.current.csr[CSR_SSP][1:0] {
        bins read_only_zero = {2'b00};
    }

    // ── Alignment building blocks ─────────────────────────────────────────
    // DH review: sweep the bottom 3 bits over all 8 values rather than
    // enumerating aligned/misaligned cases separately.
    ssp_LSBs: coverpoint ins.prev.csr[CSR_SSP][2:0] {
        // auto fills 000 through 111
    }
    ssamoswap_adr_LSBs: coverpoint ins.current.rs1_val[2:0] {
        // auto fills 000 through 111
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

    // ── Shadow stack pop match/mismatch ───────────────────────────────────
    // A mismatching SSPOPCHK raises a software-check exception; a matching one
    // retires. trap is the discriminator between the two stimulus classes.
    sspopchk_outcome: coverpoint ins.current.trap {
        bins matched    = {1'b0};
        bins mismatched = {1'b1};
    }

    // ── Enable-chain (SSE) building blocks ────────────────────────────────
    menvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    senvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // Zicfiss active for U-mode requires BOTH menvcfg.SSE and senvcfg.SSE.
    u_sse_active: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse"),
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse")} {
        bins inactive_both_off = {2'b00};
        bins inactive_men_off  = {2'b01};
        bins inactive_sen_off  = {2'b10};
        bins active            = {2'b11};
    }
    u_sse_inactive: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse"),
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse")} {
        bins both_off = {2'b00};
        bins men_off  = {2'b01};
        bins sen_off  = {2'b10};
    }

    // ── Target page / PMA building blocks ─────────────────────────────────
    // pte.xwr occupies bits [3:1] of the leaf PTE; V is bit 0.
    pte_xwr: coverpoint ins.current.pte_d[3:1] {
        bins ss_page      = {3'b010};  // R=0,W=1,X=0 — the SS page encoding
        bins read_only    = {3'b001};
        bins read_write   = {3'b011};
        bins exec_read    = {3'b101};
        bins exec_only    = {3'b100};
    }
    pte_ss_page: coverpoint ins.current.pte_d[3:1] {
        bins ss_page = {3'b010};
    }

    // ── Non-SS accessors of an SS page ────────────────────────────────────
    ordinary_storeops: coverpoint ins.current.insn {
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
        `endif
    }
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

    // ── Fault-priority building block ─────────────────────────────────────
    // SSPOPCHK's base is implicitly ssp, so the faulting address is ssp itself
    // rather than rs1+imm. Pointing ssp at the model's access-fault address while a
    // value mismatch is ALSO present is what makes this a real priority test: the
    // access-fault must win over the software-check exception.
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
    // Instruction behaviour (Zicfiss active)
    cp_ssp_access:                 cross priv_mode_u, csrops, ssp_csr, ssp_write_pattern;
    cp_ssp_low_bits_ro_zero:       cross priv_mode_u, csrops, ssp_csr, ssp_wr_low_bits, ssp_rd_low_bits;
    cp_sspush:                     cross priv_mode_u, ss_push_instr, ssp_write_pattern;
    cp_sspopchk_match:             cross priv_mode_u, ss_pop_instr, sspopchk_outcome {
        ignore_bins mismatch = binsof(sspopchk_outcome.mismatched);
    }
    cp_sspopchk_mismatch:          cross priv_mode_u, ss_pop_instr, sspopchk_outcome {
        ignore_bins match = binsof(sspopchk_outcome.matched);
    }
    cp_sspopchk_fault_priority:    cross priv_mode_u, ss_pop_instr, ssp_fault_address;
    cp_ss_call_return:             cross priv_mode_u, ss_push_instr, ss_pop_instr;
    cp_ssrdp:                      cross priv_mode_u, ssrdp_instr, u_sse_active;
    `ifdef UDB_MXLEN_64
        cp_ssamoswap:              cross priv_mode_u, ssamoswap_instr, swap_loaded_msb, swap_rs2_upper;
    `else
        cp_ssamoswap:              cross priv_mode_u, ssamoswap_instr, swap_loaded_msb;
    `endif

    // Alignment
    cp_ss_address_alignment_ssp:   cross priv_mode_u, ss_push_instr, ssp_LSBs;
    cp_ss_address_alignment_pop:   cross priv_mode_u, ss_pop_instr, ssp_LSBs;
    cp_ss_address_alignment_swap:  cross priv_mode_u, ssamoswap_instr, ssamoswap_adr_LSBs;

    // Page / PMA behaviour
    cp_ss_instr_target_page:       cross priv_mode_u, ss_mem_instr, pte_xwr;
    cp_ss_page_access_store:       cross priv_mode_u, ordinary_storeops, pte_ss_page;
    cp_ss_page_access_load:        cross priv_mode_u, ordinary_loadops, pte_ss_page;
    cp_ss_page_access_amo:         cross priv_mode_u, ordinary_amoops, pte_ss_page;
    `ifdef ZICBOM_SUPPORTED
        cp_ss_page_access_cbo:     cross priv_mode_u, cbo_ops, pte_ss_page;
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cp_ss_page_access_cboz:    cross priv_mode_u, cboz_ops, pte_ss_page;
    `endif

    // Enable-chain gating
    cp_ssp_csr_gating_u:           cross priv_mode_u, csrops, ssp_csr, u_sse_active;
    cp_ss_instr_inactive:          cross priv_mode_u, ss_mop_instr, u_sse_inactive;
    cp_ssamoswap_sse_gating:       cross priv_mode_u, ssamoswap_instr, u_sse_inactive;

endgroup

function void zicfissu_sample(int hart, int issue, ins_t ins);
    ZicfissU_cg.sample(ins);
endfunction
