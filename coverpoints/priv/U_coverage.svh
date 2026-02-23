///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 13 November 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_U
covergroup U_uprivinst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    privinstrs: coverpoint ins.current.insn  {
        bins ecall  = {ECALL};
        bins ebreak = {EBREAK};
        bins mret   = {MRET};
        bins sret   = {SRET};
    }
    // main coverpoints
    cp_uprivinst:  cross priv_mode_u, privinstrs;
endgroup

covergroup U_ucsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csr_nonuser: coverpoint ins.current.insn[31:20]  {
        bins nonuser_0[] = {[12'h100:12'h3FF]};
        bins nonuser_1[] = {[12'h500:12'h7FF]};
        bins nonuser_2[] = {[12'h900:12'hBFF]};
        bins nonuser_3[] = {[12'hD00:12'hFFF]};
    }
    csrr: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
    }
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }

    cp_csr_insufficient_priv: cross priv_mode_u, csrr, csr_nonuser, nonzerord;
endgroup


function void u_sample(int hart, int issue, ins_t ins);
    U_uprivinst_cg.sample(ins);
    U_ucsr_cg.sample(ins);
endfunction
