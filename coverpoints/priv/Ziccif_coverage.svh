///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written:  David_Harris@hmc.edu 22 October 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for Ziccif extension (main memory supports instruction fetch)
///////////////////////////////////////////////


`define COVER_ZICCIF

covergroup Ziccif_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    cp_ziccif_fetch: coverpoint ins.current.insn {
        wildcard bins add = {ADD};
        `ifdef ZCA_SUPPORTED
            wildcard bins c_add = {C_ADD};
        `endif
    }

endgroup

function void ziccif_sample(int hart, int issue, ins_t ins);
    Ziccif_cg.sample(ins);
endfunction
