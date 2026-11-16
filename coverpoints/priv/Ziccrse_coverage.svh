///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written:  David_Harris@hmc.edu 22 October 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for Ziccrse extension (main memory supports forward progress on LR/SC sequences)
///////////////////////////////////////////////


`define COVER_ZICCRSE

covergroup Ziccrse_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    lr_w_instr: coverpoint ins.prev.insn {
        wildcard bins lr_w = {LR_W};
    }
    sc_w_instr: coverpoint ins.current.insn {
        wildcard bins sc_w = {SC_W};
    }
    sc_w_pass: coverpoint ins.current.rd_val {
        bins pass = {0};
    }

    cp_ziccrse: cross lr_w_instr, sc_w_instr, sc_w_pass;

endgroup

function void ziccrse_sample(int hart, int issue, ins_t ins);
    Ziccrse_cg.sample(ins);
endfunction
