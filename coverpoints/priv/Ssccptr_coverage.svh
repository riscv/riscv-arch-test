///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Based on Ssccptr Extension Test Plan
//
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
    // Virtual memory active — check the MODE field of satp, not the whole
    // register.  The MODE field position differs by XLEN:
    //   RV64: satp[63:60] — non-zero means Sv39/Sv48/Sv57 is active
    //   RV32: satp[31]    — 1 means Sv32 is active
    // -----------------------------------------------------------------------

    `ifdef XLEN64
    satp_active: coverpoint ins.current.csr[CSR_SATP][63:60] {
            bins vm_on = {[1:$]};
    }
    `else
    satp_active: coverpoint ins.current.csr[CSR_SATP][31] {
            bins vm_on = {1'b1};
    }
    `endif

    lw_insn: coverpoint ins.current.insn {
            wildcard bins lw = {LW};
   }

    load_result_sentinel: coverpoint ins.current.rd_val[31:0] {
            bins sentinel = {32'hC0FFEE42};
   }

    cp_ssccptr: cross priv_mode_s, satp_active, lw_insn, load_result_sentinel;

endgroup

function void ssccptr_sample(int hart, int issue, ins_t ins);
    Ssccptr_cg.sample(ins);
endfunction
