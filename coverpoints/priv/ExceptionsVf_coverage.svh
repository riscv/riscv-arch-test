///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: James Kaden Cassidy jacassidy@hmc.edu June 12 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSVF

covergroup ExceptionsVf_cg with function sample(ins_t ins);
    option.per_instance = 0;

    //////////////////////////////////////////////////////////////////////////////////
    // cp_mstatus_vs_off
    // checks that floating-point vector instructions trap when mstatus.vs is inactive
    //////////////////////////////////////////////////////////////////////////////////

    misa_v_active : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "exts")[21] {
        bins vector = {1};
    }

    vector_fp_instruction : coverpoint {ins.current.insn[14:12], ins.current.insn[6:0]} {
        bins fp_arithmetic_vv_opcode = {10'b001_1010111};
    }

    mstatus_vs_inactive : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins inactive = {0};
    }

    cp_mstatus_vs_off : cross misa_v_active, mstatus_vs_inactive, vector_fp_instruction;

endgroup


function void exceptionsvf_sample(int hart, int issue, ins_t ins);
    ExceptionsVf_cg.sample(ins);
endfunction
