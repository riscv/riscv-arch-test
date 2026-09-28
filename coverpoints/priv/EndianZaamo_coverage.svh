///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ENDIANZAAMO
covergroup EndianZaamo_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // "Endianness tests for Zaamo atomic instructions"

    // building blocks for the main coverpoints
    cp_amo: coverpoint ins.current.insn {
        wildcard bins amoaddw = {AMOADD_W};
        `ifdef UDB_MXLEN_64
            wildcard bins amoaddd = {AMOADD_D};
        `endif
    }
    `ifdef UDB_MXLEN_64
        mstatus_mbe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mbe")[0] {
        }
    `else
        mstatus_mbe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "mbe")[0] {
        }
    `endif

    // main coverpoints
    cp_endianness_amo: cross priv_mode_m, mstatus_mbe, cp_amo;
endgroup

function void endianzaamo_sample(int hart, int issue, ins_t ins);
    EndianZaamo_cg.sample(ins);
endfunction
