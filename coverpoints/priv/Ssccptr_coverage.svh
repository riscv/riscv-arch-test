///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Based on Ssccptr Extension Test Plan
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Coverage for the Ssccptr extension.
//
//   Ssccptr: "Main memory supports hardware page-table walker (HPTW) reads."
//
//   When virtual memory is active (satp ≠ 0), the HPTW reads PTEs from
//   main memory to translate every virtual address.  This covergroup verifies
//   that both loads and stores succeed under VM — i.e. the HPTW can read
//   PTEs from main memory for both read and write translations.
//
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSCCPTR

covergroup Ssccptr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // -----------------------------------------------------------------------
    // Virtual memory active — satp ≠ 0 means a VM scheme is enabled.
    // -----------------------------------------------------------------------

    satp_active: coverpoint ins.current.csr[12'h180] {
            bins vm_on = {[1:$]};
    }

    // -----------------------------------------------------------------------
    // Instruction type bins — one per load/store width tested
    // -----------------------------------------------------------------------

    lw_insn:  coverpoint ins.current.insn { wildcard bins lw  = {LW};  }
    sw_insn:  coverpoint ins.current.insn { wildcard bins sw  = {SW};  }
    lh_insn:  coverpoint ins.current.insn { wildcard bins lh  = {LH};  }
    sh_insn:  coverpoint ins.current.insn { wildcard bins sh  = {SH};  }
    lb_insn:  coverpoint ins.current.insn { wildcard bins lb  = {LB};  }
    sb_insn:  coverpoint ins.current.insn { wildcard bins sb  = {SB};  }
    lhu_insn: coverpoint ins.current.insn { wildcard bins lhu = {LHU}; }
    lbu_insn: coverpoint ins.current.insn { wildcard bins lbu = {LBU}; }

    // RV64-only widths
    `ifdef XLEN64
    ld_insn:  coverpoint ins.current.insn { wildcard bins ld  = {LD};  }
    sd_insn:  coverpoint ins.current.insn { wildcard bins sd  = {SD};  }
    lwu_insn: coverpoint ins.current.insn { wildcard bins lwu = {LWU}; }
    `endif

    // -----------------------------------------------------------------------
    // Load result — the committed rd value.
    // -----------------------------------------------------------------------

    load_result_sentinel: coverpoint ins.current.rd_val[31:0] {
        bins sentinel = {32'hDEADBEEF};
    }

    // -----------------------------------------------------------------------
    // Store load-back results — sampled at the load-back instruction that
    // follows each store.  The load-back instruction is a lw/lh/lb/ld, so
    // rd_val is meaningful and carries the value read back from memory.
    //
    // sw_loadback_correct : lw  after sw  returns 0xC0FFEE00
    // sh_loadback_correct : lh  after sh  returns sign-extended 0xBEEF
    // sb_loadback_correct : lb  after sb  returns sign-extended 0xAB
    // sd_loadback_correct : ld  after sd  returns 0xC0FFEE00DEADBEEF
    // -----------------------------------------------------------------------

    sw_loadback_correct: coverpoint ins.current.rd_val[31:0] {
        bins sw_written = {32'hC0FFEE00};
    }

    sh_loadback_correct: coverpoint ins.current.rd_val[15:0] {
        bins sh_written = {16'hBEEF};
    }

    sb_loadback_correct: coverpoint ins.current.rd_val[7:0] {
        bins sb_written = {8'hAB};
    }

    `ifdef XLEN64
    sd_loadback_correct: coverpoint ins.current.rd_val {
        bins sd_written = {64'hC0FFEE00DEADBEEF};
    }
    `endif

    // -----------------------------------------------------------------------
    // Main crosses
    //
    // Load crosses: sampled at the load instruction itself — rd_val holds
    //   the loaded value directly.
    //
    // Store crosses: sampled at the load-back instruction (lw/lh/lb/ld)
    //   that immediately follows the store — rd_val holds the round-tripped
    //   value, proving the store went through a valid HPTW translation.
    //   The store instruction (sw/sh/sb/sd) is crossed via ins.prev so we
    //   confirm it was the preceding instruction.
    // -----------------------------------------------------------------------

    // Previous instruction bins — used to confirm a store preceded the load-back
    prev_sw_insn: coverpoint ins.prev.insn { wildcard bins sw = {SW}; }
    prev_sh_insn: coverpoint ins.prev.insn { wildcard bins sh = {SH}; }
    prev_sb_insn: coverpoint ins.prev.insn { wildcard bins sb = {SB}; }
    `ifdef XLEN64
    prev_sd_insn: coverpoint ins.prev.insn { wildcard bins sd = {SD}; }
    `endif

    // Primary load coverpoint — lw with sentinel check
    cp_ssccptr_load: cross priv_mode_s, satp_active, lw_insn, load_result_sentinel;

    // Primary store coverpoint — sampled at the lw load-back after sw
    cp_ssccptr_store: cross priv_mode_s, satp_active, lw_insn, prev_sw_insn, sw_loadback_correct;

    // Load width coverage
    cp_ssccptr_lh:  cross priv_mode_s, satp_active, lh_insn,  sh_loadback_correct;
    cp_ssccptr_lb:  cross priv_mode_s, satp_active, lb_insn,  sb_loadback_correct;
    cp_ssccptr_lhu: cross priv_mode_s, satp_active, lhu_insn;
    cp_ssccptr_lbu: cross priv_mode_s, satp_active, lbu_insn;

    // Store width coverage — sampled at the load-back instruction after each store
    cp_ssccptr_sh: cross priv_mode_s, satp_active, lh_insn, prev_sh_insn, sh_loadback_correct;
    cp_ssccptr_sb: cross priv_mode_s, satp_active, lb_insn, prev_sb_insn, sb_loadback_correct;

    // RV64-only width coverage
    `ifdef XLEN64
    cp_ssccptr_ld:  cross priv_mode_s, satp_active, ld_insn;
    cp_ssccptr_sd:  cross priv_mode_s, satp_active, ld_insn, prev_sd_insn, sd_loadback_correct;
    cp_ssccptr_lwu: cross priv_mode_s, satp_active, lwu_insn;
    `endif

endgroup

function void ssccptr_sample(int hart, int issue, ins_t ins);
    Ssccptr_cg.sample(ins);
endfunction
