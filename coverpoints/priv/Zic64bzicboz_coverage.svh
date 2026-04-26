///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written:  Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for RVA23U64 profile - Zic64bzicboz extension
///////////////////////////////////////////////

`define COVER_ZIC64BZICBOZ

covergroup Zic64bzicboz_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    cbo_zero: coverpoint ins.current.insn {
        wildcard bins cbo_zero = {CBO_ZERO};
    }
    cbo_zero_offset: coverpoint ins.current.rs1_val[6:0] {
        bins offset_aligned[] = {[7'd0 : 7'd64]} with (item % 4 == 0);
    }

    cp_zi64cb: cross cbo_zero, cbo_zero_offset ;

endgroup

function void zic64bzicboz_sample(int hart, int issue, ins_t ins);
    Zic64bzicboz_cg.sample(ins);
endfunction
