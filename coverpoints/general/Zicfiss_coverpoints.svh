///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Zicfiss Shared Coverpoints
//
// Building blocks shared by the Zicfiss covergroups (M, S/HS, VS/VU, U).
//
// Written: Umer Shahid umer@riscv.org 2026
//
// Copyright (C) 2026 RISC-V International
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    // ── Instruction building blocks ───────────────────────────────────────
    // Every SS instruction that accesses memory, used for page and fault crosses.
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
    ss_pop_instr: coverpoint ins.current.insn {
        wildcard bins sspopchk_x1   = {SSPOPCHK_X1};
        wildcard bins sspopchk_x5   = {SSPOPCHK_X5};
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspopchk_x5 = {C_SSPOPCHK_X5};
        `endif
    }
    ssamoswap_instr: coverpoint ins.current.insn {
        wildcard bins ssamoswap_w = {SSAMOSWAP_W};
        `ifdef UDB_MXLEN_64
            wildcard bins ssamoswap_d = {SSAMOSWAP_D};
        `endif
    }
    // MOP-encoded instructions, which revert to Zimop/Zcmop while Zicfiss is inactive.
    // SSAMOSWAP is AMO-encoded and traps instead.
    ss_mop_instr: coverpoint ins.current.insn {
        type_option.weight = 0;
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
    // SSPUSH and SSPOPCHK are architecturally defined only for x1 and x5.
    // The compressed forms exist only when Zcmop is implemented.
    ss_push_instr: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins sspush_x1   = {SSPUSH_X1};
        wildcard bins sspush_x5   = {SSPUSH_X5};
        `ifdef ZCMOP_SUPPORTED
            wildcard bins c_sspush_x1 = {C_SSPUSH_X1};
        `endif
    }
    ssrdp_instr: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins ssrdp = {SSRDP};
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
    // ssp on the shadow stack page, or on the unmapped page an active access would fault on.
    ssp_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins ss_page  = {[64'h140300000:64'h140300FFF]};
            bins unmapped = {64'h140400000};
        `else
            bins ss_page  = {[32'hC0300000:32'hC0300FFF]};
            bins unmapped = {32'hC0400000};
        `endif
    }

    // ── Enable-chain building blocks ──────────────────────────────────────
    menvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // The SSE bit alone set (csrrs) or cleared (csrrc): funct3 is insn[14:12] and SSE is
    // bit 3 of rs1. Setting or clearing only SSE leaves every other field of the CSR alone.
    sse_bit_write: coverpoint {ins.current.insn[14:12], ins.current.rs1_val[3]} {
        type_option.weight = 0;
        bins set_sse   = {4'b0101};
        bins clear_sse = {4'b0111};
    }

    // ── Page building blocks ──────────────────────────────────────────────
    pte_ss_page: coverpoint ins.current.pte_d[3:1] iff (ins.current.pte_d[0]) {
        bins ss_page = {3'b010};
    }
    // pte.xwr of the PTE the walk ended on. 000 at the last level is a pointer where a
    // leaf is required and 110 is reserved, so both fail the walk itself.
    pte_xwr: coverpoint ins.current.pte_d[3:1] iff (ins.current.pte_d[0]) {
        type_option.weight = 0;
        bins non_leaf        = {3'b000};
        bins read_only       = {3'b001};
        bins ss_page         = {3'b010};
        bins read_write      = {3'b011};
        bins exec_only       = {3'b100};
        bins exec_read       = {3'b101};
        bins rsvd_wx         = {3'b110};
        bins read_write_exec = {3'b111};
    }
    // pte.U is bit 4.
    pte_u: coverpoint ins.current.pte_d[4] {
        type_option.weight = 0;
        bins supervisor = {1'b0};
        bins user       = {1'b1};
    }
    // MXR governs whether an R=0 page is readable; the SS page is R=0 by construction.
    sstatus_mxr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
        type_option.weight = 0;
        bins mxr_clear = {1'b0};
        bins mxr_set   = {1'b1};
    }
    ordinary_storeops: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
        `endif
    }

    // Low three bits of an ordinary store's effective address.
    store_addr_lsb: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] {
        type_option.weight = 0;
        // auto fills 000 through 111
    }
    // Zicfiss uses only some encodings of mop.rr.7 and mop.r.28. The rest stay Zimop/Zcmop.
    // Each register field is swept over all 32 registers with the other fields held at a fixed
    // value. The ignored bins are the Zicfiss instructions: SSPUSH (rd = rs1 = x0, rs2 = x1/x5),
    // SSPOPCHK (rd = x0, rs1 = x1/x5) and SSRDP (rs1 = x0).
    mop_rr7_rs2: coverpoint ins.current.insn[24:20]
        iff (ins.current.insn ==? MOP_RR_7 && ins.current.insn[11:7] == 0 && ins.current.insn[19:15] == 0) {
        type_option.weight = 0;
        ignore_bins sspush = {1, 5};
    }
    mop_rr7_rs1: coverpoint ins.current.insn[19:15]
        iff (ins.current.insn ==? MOP_RR_7 && ins.current.insn[11:7] == 0 && ins.current.insn[24:20] == 1) {
        type_option.weight = 0;
        ignore_bins sspush = {0};
    }
    mop_rr7_rd: coverpoint ins.current.insn[11:7]
        iff (ins.current.insn ==? MOP_RR_7 && ins.current.insn[19:15] == 0 && ins.current.insn[24:20] == 1) {
        type_option.weight = 0;
        ignore_bins sspush = {0};
    }
    mop_r28_rs1: coverpoint ins.current.insn[19:15]
        iff (ins.current.insn ==? MOP_R_28 && ins.current.insn[11:7] == 0) {
        type_option.weight = 0;
        ignore_bins sspopchk = {1, 5};
    }
    mop_r28_rd: coverpoint ins.current.insn[11:7]
        iff (ins.current.insn ==? MOP_R_28 && ins.current.insn[19:15] == 1) {
        type_option.weight = 0;
        ignore_bins sspopchk = {0};
    }
    `ifdef ZCMOP_SUPPORTED
        // c.mop.1 and c.mop.5 are C.SSPUSH x1 and C.SSPOPCHK x5.
        mop_c: coverpoint ins.current.insn {
            type_option.weight = 0;
            wildcard bins c_mop_3 = {C_MOP_3};
            wildcard bins c_mop_7 = {C_MOP_7};
        }
    `endif

    // ── Alignment building blocks ─────────────────────────────────────────
    // ssp[1:0] are read-only zero, and so is ssp[2] unless UXLEN or SXLEN can be 32. The
    // test writes all eight low-bit values; only these can be held.
    ssp_LSBs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp")[2:0] {
        type_option.weight = 0;
        bins aligned_8 = {3'b000};
        `ifdef ZICFISS_SSP_BIT2_WRITABLE
            bins aligned_4 = {3'b100};
        `endif
    }
    ssamoswap_adr_LSBs: coverpoint ins.current.rs1_val[2:0] {
        type_option.weight = 0;
        // auto fills 000 through 111
    }

    // ── Fault building blocks ─────────────────────────────────────────────
    // SSPOPCHK's base is implicitly ssp, so the faulting address is ssp itself.
    ssp_fault_address: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            bins unmapped = {64'h140400000};
        `else
            bins unmapped = {32'hC0400000};
        `endif
    }
    // A mismatching SSPOPCHK raises a software-check exception; a matching one retires.
    // trap is the discriminator between the two stimulus classes.
    sspopchk_outcome: coverpoint ins.current.trap {
        type_option.weight = 0;
        bins matched    = {1'b0};
        bins mismatched = {1'b1};
    }
    // On a software-check exception stval reports shadow stack fault (code 3), or 0 if the
    // implementation provides no information.
    // Guarded on the trap being taken by this instruction, since the CSR array is persistent.
    stval_ss_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval")
                    iff (ins.current.csr_wb[CSR_SEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sepc", "sepc") == ins.current.pc_rdata)) {
        type_option.weight = 0;
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
        type_option.weight = 0;
        bins sw_check = {SOFTWARE_CHECK};
    }
