///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: ammarahwakeel9@gmail.com (UET Lahore, APRIL 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for RVA23 profile - Ssu64x extension
//
///////////////////////////////////////////////

`define COVER_SSU64XL

covergroup Ssu64xl_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    sstatus_uxl: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "uxl") {
        bins uxl_sstatus = {2'b10};
    }

    gpr_bit63: coverpoint ins.current.rd_val[63] {
        bins bit63_set = {1'b1};
    }

    cp_ssu64xl_UXLEN: cross priv_mode_u, sstatus_uxl, gpr_bit63;

endgroup

function void ssu64xl_sample(int hart, int issue, ins_t ins);
    Ssu64xl_cg.sample(ins);
endfunction
