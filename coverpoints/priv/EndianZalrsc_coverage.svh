///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ENDIANZALRSC
covergroup EndianZalrsc_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // "Endianness tests for Zalrsc atomic instructions"

    // building blocks for the main coverpoints
    cp_lr: coverpoint ins.current.insn {
        wildcard bins lrw = {LR_W};
        `ifdef XLEN64
            wildcard bins lrd = {LR_D};
        `endif
    }
    cp_sc: coverpoint ins.current.insn {
        wildcard bins scw = {SC_W};
        `ifdef XLEN64
            wildcard bins scd = {SC_D};
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
    cp_endianness_lr: cross priv_mode_m, mstatus_mbe, cp_lr;
    cp_endianness_sc: cross priv_mode_m, mstatus_mbe, cp_sc;
endgroup

function void endianzalrsc_sample(int hart, int issue, ins_t ins);
    EndianZalrsc_cg.sample(ins);
endfunction
