///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — U-mode coverage
//
// Written: Umer Shahid umer@riscv.org 2026
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICFISSU

// ssp[2] is writable only when UXLEN or SXLEN can be 32
`ifdef UDB_UXLEN_32
    `define ZICFISS_SSP_BIT2_WRITABLE
`elsif UDB_SXLEN_32
    `define ZICFISS_SSP_BIT2_WRITABLE
`endif

covergroup ZicfissU_cg with function sample(ins_t ins);
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
    cp_ssamoswap_aqrl:             cross priv_mode_u, ssamoswap_instr, swap_aqrl;
    cp_ssamoswap_reg_edges:        cross priv_mode_u, ssamoswap_instr, swap_reg_edge;

    // Alignment
    cp_ss_address_alignment_ssp:   cross priv_mode_u, ss_push_instr, ssp_LSBs;
    cp_ss_address_alignment_pop:   cross priv_mode_u, ss_pop_instr, ssp_LSBs;
    // The misaligned atomicity granule applies only to Zaamo, Zabha and Zacas AMOs
    // (norm:pma_mag_insts), so every misaligned SSAMOSWAP faults.
    cp_ss_address_alignment_swap:  cross priv_mode_u, ssamoswap_instr, ssamoswap_adr_LSBs;

    // Page / PMA behaviour
    cp_ss_instr_target_page:       cross priv_mode_u, ss_mem_instr, pte_xwr;
    // The SS page's U bit and sstatus.MXR: a U=0 page faults in translation from U-mode, and
    // MXR has no effect on an SS instruction's access to the R=0 SS page.
    cp_ss_instr_target_page_u_mxr: cross priv_mode_u, ss_mem_instr, pte_ss_page, pte_u, sstatus_mxr;

    // A push at the base of a page writes into the preceding page; a pop reads the
    // page ssp is already on. The fault follows the page actually accessed.
    cp_ss_page_crossing:           cross priv_mode_u, ss_stack_instr, ssp_page_offset;

    // pte.A / pte.D: SSPUSH and SSAMOSWAP write and so need D; SSPOPCHK only reads.
    cp_ss_page_ad_bits:            cross priv_mode_u, ss_mem_instr, pte_ad;

    `ifdef SVPBMT_SUPPORTED
        // PBMT=IO makes the page non-idempotent, which SS instructions must reject; NC memory is
        // idempotent.
        // Known coverage gap: the SSAMOSWAP x PBMT=NC bins are not tested. An implementation may
        // override the AMO PMA of an NC page (norm:Svpbmt_impl_may_override_pmas), so the outcome
        // is implementation-defined, and no UDB parameter yet says which behavior a DUT has.
        cp_ss_non_idempotent:      cross priv_mode_u, ss_mem_instr, pte_pbmt, menvcfg_pbmte;
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

endgroup

function void zicfissu_sample(int hart, int issue, ins_t ins);
    ZicfissU_cg.sample(ins);
endfunction
