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
    // ssp[1:0] are always read-only zero. ssp[2] is read-only zero as well when UXLEN
    // and SXLEN can never be 32, so sample all three and let the signature comparison
    // against the reference model decide which bits this config holds at zero.
    `ifdef UDB_MXLEN_64
        ssp_rd_low_bits: coverpoint ins.current.csr[CSR_SSP][2:0] {
            bins read_only_zero = {3'b000};
        }
    `else
        ssp_rd_low_bits: coverpoint ins.current.csr[CSR_SSP][1:0] {
            bins read_only_zero = {2'b00};
        }
    `endif

    // ── Alignment building blocks ─────────────────────────────────────────
    // Sweep the bottom 3 bits over all 8 values.
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
    // menvcfg.SSE=0 forces senvcfg.SSE read-only zero, so {menvcfg=0, senvcfg=1} is
    // architecturally unreachable. The test still attempts it; the bin is illegal so an
    // implementation that allows it is flagged rather than silently covered.
    u_sse_active: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                              (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1)} {
        bins inactive_both_off = {2'b00};
        bins inactive_sen_off  = {2'b10};
        bins active            = {2'b11};
        illegal_bins men0_sen1 = {2'b01};
    }
    u_sse_inactive: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1)} {
        bins both_off = {2'b00};
        bins sen_off  = {2'b10};
        illegal_bins men0_sen1 = {2'b01};
    }

    // ── Target page / PMA building blocks ─────────────────────────────────
    // pte.xwr occupies bits [3:1] of the leaf PTE; V is bit 0.
    // All eight encodings: 000 is a pointer rather than a leaf, 110 and 111 are
    // reserved, and those fail the walk itself rather than the shadow stack check.
    pte_xwr: coverpoint ins.current.pte_d[3:1] {
        bins non_leaf     = {3'b000};
        bins read_only    = {3'b001};
        bins ss_page      = {3'b010};
        bins read_write   = {3'b011};
        bins exec_only    = {3'b100};
        bins exec_read    = {3'b101};
        bins rsvd_wx      = {3'b110};
        bins rsvd_rwx     = {3'b111};
    }
    // pte.U is bit 4; pte.A is bit 6 and pte.D is bit 7.
    pte_u: coverpoint ins.current.pte_d[4] {
        bins supervisor = {1'b0};
        bins user       = {1'b1};
    }
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
    `endif
    // MXR governs whether an R=0 page is readable; the SS page is R=0 by construction.
    sstatus_mxr: coverpoint ins.prev.csr[CSR_SSTATUS][19] {
        bins mxr_clear = {1'b0};
        bins mxr_set   = {1'b1};
    }
    // Where ssp sits inside its page. A push decrements before storing, so a pointer
    // at the page base writes into the preceding page.
    ssp_page_offset: coverpoint ins.prev.csr[CSR_SSP][11:0] {
        bins at_page_base = {12'h000};
        bins near_base    = {[12'h001:12'h010]};
        bins mid_page     = {[12'h011:12'hFEF]};
        bins near_top     = {[12'hFF0:12'hFFF]};
    }
    pte_ss_page: coverpoint ins.current.pte_d[3:1] {
        bins ss_page = {3'b010};
    }
    // The Sail->RVVI converter does not populate pte_d, so page identity is taken from
    // the address instead. The shadow stack, read/write and read-only test pages are
    // laid out one after another, so VA[13:12] identifies which one is being touched.
    ss_target_page: coverpoint ins.prev.csr[CSR_SSP][13:12] {
        bins ss_page    = {2'd0};
        bins rw_page    = {2'd1};
        bins ro_page    = {2'd2};
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
    // The immediate CSR forms carry a 5-bit uimm, so rs1_val can never be all-ones
    // for them. Excluded as unreachable rather than left as a permanent hole.
    cp_ssp_access:                 cross priv_mode_u, csrops, ssp_csr, ssp_write_pattern {
        ignore_bins imm_cannot_be_all_ones =
            (binsof(csrops.csrrwi) || binsof(csrops.csrrsi) || binsof(csrops.csrrci)) &&
            binsof(ssp_write_pattern.all_ones);
    }
    cp_ssp_low_bits_ro_zero:       cross priv_mode_u, csr_reg_ops, ssp_csr, ssp_wr_low_bits, ssp_rd_low_bits;
    cp_sspush:                     cross priv_mode_u, ss_push_instr, ssp_write_pattern, pte_ss_page;
    cp_sspopchk_match:             cross priv_mode_u, ss_pop_instr, sspopchk_outcome, pte_ss_page {
        ignore_bins mismatch = binsof(sspopchk_outcome.mismatched);
    }
    cp_sspopchk_mismatch:          cross priv_mode_u, ss_pop_instr, sspopchk_outcome, pte_ss_page {
        ignore_bins match = binsof(sspopchk_outcome.matched);
    }
    cp_sspopchk_fault_priority:    cross priv_mode_u, ss_pop_instr, ssp_fault_address;
    cp_ss_call_return:             cross priv_mode_u, ss_pop_instr, sspopchk_outcome, pte_ss_page;
    cp_ssrdp:                      cross priv_mode_u, ssrdp_instr, u_sse_active;
    `ifdef UDB_MXLEN_64
        cp_ssamoswap:              cross priv_mode_u, ssamoswap_instr, swap_loaded_msb, swap_rs2_upper, pte_ss_page;
    `else
        cp_ssamoswap:              cross priv_mode_u, ssamoswap_instr, swap_loaded_msb, pte_ss_page;
    `endif
    cp_ssamoswap_aqrl:             cross priv_mode_u, ssamoswap_instr, swap_aqrl;
    cp_ssamoswap_reg_edges:        cross priv_mode_u, ssamoswap_instr, swap_reg_edge;

    // Alignment
    cp_ss_address_alignment_ssp:   cross priv_mode_u, ss_push_instr, ssp_LSBs;
    cp_ss_address_alignment_pop:   cross priv_mode_u, ss_pop_instr, ssp_LSBs;
    cp_ss_address_alignment_swap:  cross priv_mode_u, ssamoswap_instr, ssamoswap_adr_LSBs;

    // Page / PMA behaviour
    cp_ss_instr_target_page:       cross priv_mode_u, ss_mem_instr, ss_target_page;

    // A push at the base of a page writes into the preceding page; a pop reads the
    // page ssp is already on. The fault follows the page actually accessed.
    cp_ss_page_crossing:           cross priv_mode_u, ss_mem_instr, ssp_page_offset;

    // pte.A / pte.D: SSPUSH and SSAMOSWAP write and so need D; SSPOPCHK only reads.
    cp_ss_page_ad_bits:            cross priv_mode_u, ss_mem_instr, pte_ad;

    `ifdef SVPBMT_SUPPORTED
        // PBMT=IO makes the page non-idempotent, which SS instructions must reject.
        cp_ss_non_idempotent:      cross priv_mode_u, ss_mem_instr, pte_pbmt;
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
    // Vector accessor leg deferred: it needs V in the suite's required_extensions and
    // vector setup in the generator. Tracked on the ZicfissU test plan row rather than
    // shipped as a coverpoint that can never fill.

    // Enable-chain gating
    cp_ssp_csr_gating_u:           cross priv_mode_u, csrops, ssp_csr, u_sse_active;
    cp_ssamoswap_sse_gating:       cross priv_mode_u, ssamoswap_instr, u_sse_inactive;

endgroup

function void zicfissu_sample(int hart, int issue, ins_t ins);
    ZicfissU_cg.sample(ins);
endfunction
