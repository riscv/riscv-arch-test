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
    // The PMP test needs two usable entries: entry 0 for the SS page, entry 1 for the rest.
    `ifdef UDB_NUM_USABLE_PMP_ENTRIES
    `ifndef UDB_NUM_USABLE_PMP_ENTRIES_0
    `ifndef UDB_NUM_USABLE_PMP_ENTRIES_1
        pmp0_rw: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "pmpcfg0", "pmp0cfg_xwr")[1:0] {
            bins no_perm    = {2'b00};
            bins read_only  = {2'b01};
            bins read_write = {2'b11};
        }
    `endif
    `endif
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

    // ── Enable-chain building blocks ──────────────────────────────────────
    menvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
        bins sse_on  = {1'b1};
    }
    // Zicfiss is inactive in S-mode only while menvcfg.SSE=0.
    s_sse_inactive: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "sse") {
        bins sse_off = {1'b0};
    }
    // What senvcfg.SSE actually reads back afterwards. With menvcfg.SSE=0 this must
    // stay zero no matter what was written.
    senvcfg_sse_readback: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "sse") {
        bins reads_zero = {1'b0};
        bins reads_one  = {1'b1};
    }
    `ifdef H_SUPPORTED
        henvcfg_sse_readback: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "henvcfg", "sse") {
            bins reads_zero = {1'b0};
            bins reads_one  = {1'b1};
        }
        henvcfg_sse: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "sse") {
            bins sse_off = {1'b0};
            bins sse_on  = {1'b1};
        }
    `endif

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
    // SSAMOSWAP at M faults unconditionally — sweep every axis that might wrongly
    // be treated as a precondition.
    cp_ssamoswap_mmode_fault:      cross priv_mode_m, ssamoswap_instr, menvcfg_sse, satp_mode;

    // menvcfg.SSE gates ssp CSR access from S/HS.
    cp_menvcfg_sse_gating:         cross priv_mode_m_s, csrops, ssp_csr, menvcfg_sse;

    // Shadow stack instructions require PMP read-write permission, including SSPOPCHK
    // which only reads. The denied case also proves the PMP fault outranks the
    // software-check exception a value mismatch would raise.
    `ifdef UDB_NUM_USABLE_PMP_ENTRIES
    `ifndef UDB_NUM_USABLE_PMP_ENTRIES_0
    `ifndef UDB_NUM_USABLE_PMP_ENTRIES_1
        cp_ss_pmp_permissions:         cross priv_mode_s, ss_mem_instr, pmp0_rw;
    `endif
    `endif
    `endif

    // Below M-mode with satp.MODE=Bare, every SS memory access raises a store/AMO access fault.
    cp_ss_satp_bare:               cross priv_mode_s_u, ss_mem_instr, ss_active_below_m, satp_bare;

    // This suite boots to M-mode, which leaves medeleg at zero, so a software-check exception
    // from S-mode is taken in M-mode and reports shadow stack fault (code 3) in mtval.
    // Guarded on the trap being taken by this instruction, since the CSR array is persistent.
    sw_check_m: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "mcause")
                iff (ins.current.csr_wb[CSR_MEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mepc", "mepc") == ins.current.pc_rdata)) {
        bins cause_18 = {SOFTWARE_CHECK};
    }
    mtval_ss_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtval", "mtval")
                    iff (ins.current.csr_wb[CSR_MEPC] && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mepc", "mepc") == ins.current.pc_rdata)) {
        bins ss_fault = {3};
    }
    cp_ss_swcheck_mtval:           cross priv_mode_s, ss_pop_instr, sw_check_m, mtval_ss_fault;

    // Zicfiss inactive: MOP-encoded instructions stay inert, even with an ssp that an
    // active instruction would fault on. At M-mode this holds for every SSE state; S-mode
    // is gated by menvcfg.SSE alone. The U-mode leg is cp_ss_instr_inactive_u in ZicfissU.
    cp_ss_instr_inactive_m:        cross priv_mode_m, ss_mop_instr, sse_state, ssp_state;
    cp_ss_instr_inactive_s:        cross priv_mode_s, ss_mop_instr, s_sse_inactive, ssp_state;

    // With menvcfg.SSE=0 the xwr=010 encoding is reserved below M-mode, so ordinary accesses
    // page-fault; with menvcfg.SSE=1 it is an SS page, readable by loads and not writable by stores.
    cp_menvcfg_sse_ss_page:        cross priv_mode_s_u, ls_op, pte_ss_page, menvcfg_sse;

    // menvcfg.SSE=0 forces senvcfg.SSE (and henvcfg.SSE) read-only zero.
    cp_envcfg_sse_rdonly0_senvcfg: cross priv_mode_m, senvcfg_csr, menvcfg_sse, sse_bit_write, senvcfg_sse_readback {
        // The write that is sampled here is logged with its legalized value, so a read-back
        // of 1 while menvcfg.SSE=0 is an error.
        illegal_bins rdonly0_cannot_read_one =
            binsof(menvcfg_sse.sse_off) && binsof(senvcfg_sse_readback.reads_one);
        // With menvcfg.SSE=1 the field is writable and reads back what was written.
        ignore_bins writable_reads_back =
            binsof(menvcfg_sse.sse_on) &&
            ((binsof(sse_bit_write.set_sse) && binsof(senvcfg_sse_readback.reads_zero)) ||
             (binsof(sse_bit_write.clear_sse) && binsof(senvcfg_sse_readback.reads_one)));
    }
    // H_SUPPORTED is undefined for coverage until Sail supports the hypervisor extension (see
    // riscv_arch_test.sv), so these crosses and their stimulus are dormant until then.
    `ifdef H_SUPPORTED
        cp_envcfg_sse_rdonly0_henvcfg: cross priv_mode_m, henvcfg_csr, menvcfg_sse, sse_bit_write, henvcfg_sse_readback {
            illegal_bins rdonly0_cannot_read_one =
                binsof(menvcfg_sse.sse_off) && binsof(henvcfg_sse_readback.reads_one);
            // With menvcfg.SSE=1 henvcfg.SSE is writable and reads back what was written.
            ignore_bins writable_reads_back =
                binsof(menvcfg_sse.sse_on) &&
                ((binsof(sse_bit_write.set_sse) && binsof(henvcfg_sse_readback.reads_zero)) ||
                 (binsof(sse_bit_write.clear_sse) && binsof(henvcfg_sse_readback.reads_one)));
        }
        // henvcfg.SSE=0 makes senvcfg.SSE read-only zero when V=1 (menvcfg.SSE=1 here).
        cp_envcfg_sse_rdonly0_virt: cross priv_mode_vs, senvcfg_csr, henvcfg_sse, sse_bit_write, senvcfg_sse_readback {
            illegal_bins rdonly0_cannot_read_one =
                binsof(henvcfg_sse.sse_off) && binsof(senvcfg_sse_readback.reads_one);
            // With henvcfg.SSE=1 senvcfg.SSE is writable and reads back what was written.
            ignore_bins writable_reads_back =
                binsof(henvcfg_sse.sse_on) &&
                ((binsof(sse_bit_write.set_sse) && binsof(senvcfg_sse_readback.reads_zero)) ||
                 (binsof(sse_bit_write.clear_sse) && binsof(senvcfg_sse_readback.reads_one)));
        }
    `endif

endgroup

function void zicfisssm_sample(int hart, int issue, ins_t ins);
    ZicfissSm_cg.sample(ins);
endfunction
