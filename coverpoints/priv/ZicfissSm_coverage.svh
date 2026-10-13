///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Zicfiss (shadow stack) — M-mode control-plane coverage
//
// Testplan: the ZicfissSm sheet linked from docs/ctp/src/privmisc23.adoc.
//
// Written: Umer Shahid umer@riscv.org 2026
//
// Copyright (C) 2026 RISC-V International
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

// The PMP test covers the 4 KiB shadow stack page with PMP entry 0 as one NAPOT region and the
// rest of memory with entry 1. It needs NAPOT, a granularity of at most 4 KiB (G <= 12) and two
// usable entries.
`ifdef UDB_PMP_NAPOT_SUPPORTED
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_0
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_1
    `ifdef UDB_PMP_GRANULARITY_2
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_3
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_4
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_5
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_6
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_7
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_8
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_9
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_10
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_11
        `define ZICFISS_PMP_TEST
    `elsif UDB_PMP_GRANULARITY_12
        `define ZICFISS_PMP_TEST
    `endif
`endif
`endif
`endif

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
    // ssp on the shadow stack page, or on the unmapped page an active access would fault on.
    ssp_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "ssp", "ssp") {
        `ifdef UDB_MXLEN_64
            bins ss_page  = {[64'h140300000:64'h140300FFF]};
            bins unmapped = {64'h140400000};
        `else
            bins ss_page  = {[32'hC0300000:32'hC0300FFF]};
            bins unmapped = {32'hC0400000};
        `endif
    }
    // menvcfg.SSE x senvcfg.SSE. menvcfg.SSE=0 forces senvcfg.SSE read-only zero. Clearing menvcfg.SSE does not re-log
    // senvcfg, so until the next senvcfg write the trace can still show senvcfg.SSE=1; ANDing with
    // menvcfg.SSE gives the effective value. An explicit senvcfg write is logged legalized.
    sse_state: coverpoint {(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1),
                           ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1 &&
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))} {
        bins men0_sen0 = {2'b00};
        bins men1_sen0 = {2'b10};
        bins men1_sen1 = {2'b11};
    }
    // pmp0cfg R is bit 0, W is bit 1. Shadow stack instructions require read-write.
    // R=0 with W=1 is a reserved combination, so it cannot be configured.
    `ifdef ZICFISS_PMP_TEST
        pmp0_rw: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "pmpcfg0", "pmp0cfg_xwr")[1:0] {
            bins no_perm    = {2'b00};
            bins read_only  = {2'b01};
            bins read_write = {2'b11};
        }
    `endif
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
    // The SSE bit alone set (csrrs) or cleared (csrrc): funct3 is insn[14:12] and SSE is
    // bit 3 of rs1. Setting or clearing only SSE leaves every other field of the CSR alone.
    sse_bit_write: coverpoint {ins.current.insn[14:12], ins.current.rs1_val[3]} {
        bins set_sse   = {4'b0101};
        bins clear_sse = {4'b0111};
    }
    // Ordinary word/doubleword load and store, for the SS page encoding check.
    `ifdef UDB_MXLEN_64
        ls_op: coverpoint ins.current.insn {
            wildcard bins load  = {LD};
            wildcard bins store = {SD};
        }
    `else
        ls_op: coverpoint ins.current.insn {
            wildcard bins load  = {LW};
            wildcard bins store = {SW};
        }
    `endif
    pte_ss_page: coverpoint ins.current.pte_d[3:1] {
        bins ss_page = {3'b010};
    }
    `ifdef SVPBMT_SUPPORTED
        // pte.PBMT is bits [62:61]: 00 PMA, 10 IO. IO is non-idempotent.
        pte_pbmt_pma_io: coverpoint ins.current.pte_d[62:61] {
            bins pma = {2'b00};
            bins io  = {2'b10};
        }
    `endif
    // mstatus.MPRV with MPP=S makes M-mode loads and stores S-mode accesses.
    // The effective privilege mode stays M with MPRV=0, or with MPRV=1 and MPP=M.
    mprv_eff_m: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv")[0],
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
        wildcard bins mprv_clear = {3'b0??};
        bins mprv_mpp_m          = {3'b111};
    }
    mprv_mpp_s: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv")[0],
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
        bins mprv_mpp_s = {3'b101};
    }

    // ── Enable-chain building blocks ──────────────────────────────────────
    menvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // Zicfiss is inactive in S-mode only while menvcfg.SSE=0.
    s_sse_inactive: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
    }

    // ── Translation-mode building blocks ──────────────────────────────────
    // SSAMOSWAP must fault at M regardless of satp.MODE, so sweep Bare vs non-Bare.
    `ifdef UDB_MXLEN_64
        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
            bins bare     = {4'b0000};
            bins translating = {[4'b1000:4'b1011]};
        }
        satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
            bins bare = {4'b0000};
        }
    `else
        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins bare        = {1'b0};
            bins translating = {1'b1};
        }
        satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins bare = {1'b0};
        }
    `endif
    // Zicfiss active in the mode the instruction runs in: menvcfg.SSE=1, and senvcfg.SSE=1 too in U-mode.
    ss_active_below_m: coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") == 1) &&
                                   ((ins.prev.mode == 2'b01) ||
                                    (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "sse") == 1))) {
        bins active = {1'b1};
    }
    // ── Main coverpoints ──────────────────────────────────────────────────
    // SSAMOSWAP faults whenever the effective privilege mode is M — sweep every axis that might
    // wrongly be treated as a precondition, and MPRV=1 with MPP=M.
    cp_ssamoswap_mmode_fault:      cross priv_mode_m, ssamoswap_instr, menvcfg_sse, satp_mode, mprv_eff_m;
    // With MPRV=1 and MPP=S the effective privilege mode is S (menvcfg.SSE=1): satp.MODE=Bare gives a
    // store/AMO access fault, and with translation the swap completes on the S-mode SS page.
    cp_ssamoswap_mprv_s:           cross priv_mode_m, ssamoswap_instr, mprv_mpp_s, satp_mode;

    // With MPRV=1 and MPP=S the effective privilege mode is S, so SSAMOSWAP follows the S-mode
    // shadow stack rules: it completes on a PBMT=PMA page and faults on a non-idempotent PBMT=IO one.
    `ifdef SVPBMT_SUPPORTED
        cp_ssamoswap_mprv_non_idempotent: cross priv_mode_m, ssamoswap_instr, mprv_mpp_s, pte_ss_page, pte_pbmt_pma_io;
    `endif

    // menvcfg.SSE gates ssp CSR access from S/HS.
    cp_menvcfg_sse_gating:         cross priv_mode_m_s, csrops, ssp_csr, menvcfg_sse;

    // Shadow stack instructions require PMP read-write permission, including SSPOPCHK
    // which only reads. The denied case also proves the PMP fault outranks the
    // software-check exception a value mismatch would raise.
    `ifdef ZICFISS_PMP_TEST
        cp_ss_pmp_permissions:         cross priv_mode_s, ss_mem_instr, pmp0_rw;
    `endif

    // Below M-mode with satp.MODE=Bare, every SS memory access raises a store/AMO access fault.
    cp_ss_satp_bare:               cross priv_mode_s_u, ss_mem_instr, ss_active_below_m, satp_bare;

    // This suite boots to M-mode, which leaves medeleg at zero, so a software-check exception
    // from S-mode is taken in M-mode and reports shadow stack fault (code 3) in mtval, or 0 if
    // the implementation provides no information.
    // Guarded on the trap being taken by this instruction, since the CSR array is persistent.
    sw_check_m: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "mcause")
                iff (ins.current.csr_wb[CSR_MEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mepc", "mepc") == ins.current.pc_rdata)) {
        bins cause_18 = {SOFTWARE_CHECK};
    }
    mtval_ss_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtval", "mtval")
                    iff (ins.current.csr_wb[CSR_MEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mepc", "mepc") == ins.current.pc_rdata)) {
        `ifdef UDB_REPORT_CAUSE_IN_MTVAL_ON_SHADOW_STACK_SOFTWARE_CHECK
            bins ss_fault = {3};
        `else
            bins no_info = {0};
        `endif
    }
    cp_ss_swcheck_mtval:           cross priv_mode_s, ss_pop_instr, sw_check_m, mtval_ss_fault;

    // Zicfiss inactive: MOP-encoded instructions stay inert, even with an ssp that an
    // active instruction would fault on. At M-mode this holds for every SSE state; S-mode
    // is gated by menvcfg.SSE alone. The U-mode leg is cp_ss_instr_inactive_u in ZicfissU.
    cp_ss_instr_inactive_m:        cross priv_mode_m, ss_mop_instr, sse_state, ssp_state;
    cp_ss_instr_inactive_s:        cross priv_mode_s, ss_mop_instr, s_sse_inactive, ssp_state;

    // With menvcfg.SSE=0 the xwr=010 encoding is reserved below M-mode, so ordinary accesses
    // page-fault; with menvcfg.SSE=1 it is an SS page, readable by loads and not writable by stores.
    // senvcfg.SSE does not change the encoding, so U-mode with senvcfg.SSE=0 still sees an SS page.
    cp_menvcfg_sse_ss_page:        cross priv_mode_s_u, ls_op, pte_ss_page, sse_state;

    // Set and clear senvcfg.SSE and henvcfg.SSE under both values of menvcfg.SSE; the signature
    // checks that they read back 0 whenever menvcfg.SSE is 0.
    cp_envcfg_sse_rdonly0_senvcfg: cross priv_mode_m, senvcfg_csr, menvcfg_sse, sse_bit_write;
    // The V=1 leg, henvcfg.SSE=0 forcing senvcfg.SSE read-only zero, belongs to
    // ZicfissH_cg (cp_envcfg_sse_rdonly0_virt).
    `ifdef H_SUPPORTED
        cp_envcfg_sse_rdonly0_henvcfg: cross priv_mode_m, henvcfg_csr, menvcfg_sse, sse_bit_write;
    `endif

endgroup

function void zicfisssm_sample(int hart, int issue, ins_t ins);
    ZicfissSm_cg.sample(ins);
endfunction
