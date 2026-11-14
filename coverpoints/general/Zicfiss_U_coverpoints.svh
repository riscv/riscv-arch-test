///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Zicfiss U-group Coverpoints
//
// Building blocks of the Zicfiss_U coverpoints, shared by Zicfiss_U_cg and by Zicfiss_H_cg,
// which re-runs those coverpoints in VS-mode and VU-mode.
//
// Written: Umer Shahid umer@riscv.org 2026
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

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
    swap_loaded_msb: coverpoint ins.current.rd_val[31] {}
    // Only rs2[31:0] is stored by SSAMOSWAP.W — prove rs2[63:32] was non-zero
    // at least once so the "upper bits ignored" case is actually exercised.
    `ifdef UDB_MXLEN_64
        swap_rs2_upper: coverpoint (|ins.current.rs2_val[63:32]) {}
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

    // Where ssp sits inside its page. A push decrements before storing, so a pointer
    // at the page base writes into the preceding page.
    ssp_page_offset: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_SSP)[11:0] {
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

    // A jump to the shadow stack page: the fetch there must raise an instruction access fault
    // (implicit accesses to an SS page are not permitted), not an instruction page fault.
    jalr_instr: coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }
    jalr_target_ss_page: coverpoint (ins.current.eff_addr & ~1) {
        `ifdef UDB_MXLEN_64
            bins ss_page = {[64'h140300000:64'h140300FFF]};
        `else
            bins ss_page = {[32'hC0300000:32'hC0300FFF]};
        `endif
    }
    // The fetch fault is recorded with the jalr, the last instruction that retired before it.
    scause_fetch_access: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                         iff (ins.current.csr_wb[CSR_SEPC]) {
        bins access_fault = {INSTRUCTION_ACCESS_FAULT};
    }
