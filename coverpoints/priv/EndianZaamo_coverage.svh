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
        `ifdef XLEN64
            wildcard bins amoaddd = {AMOADD_D};
        `endif
    }
    `ifdef XLEN64
        mstatus_mbe: coverpoint ins.current.csr[CSR_MSTATUS][37] { // mbe is mstatus[37] in RV64
        }
    `else
        mstatus_mbe: coverpoint ins.current.csr[CSR_MSTATUSH][5] { // mbe is mstatush[5] in RV32
        }
    `endif

    // main coverpoints
    cp_endianness_amo: cross priv_mode_m, mstatus_mbe, cp_amo;
endgroup

function void endianzaamo_sample(int hart, int issue, ins_t ins);
    EndianZaamo_cg.sample(ins);
endfunction
