///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Shcounterenw: hcounteren bits are writable for implemented hpmcounters.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SHCOUNTERENW
covergroup Shcounterenw_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    hcounteren: coverpoint ins.current.insn[31:20] {
        bins hcounteren = {CSR_HCOUNTEREN};
    }
    hcounteren_write: coverpoint ins.current.rs1_val[31:0] {
        bins zeros = {32'h0};
        bins ones  = {32'hFFFFFFFF};
    }

    cp_shcounterenw: cross priv_mode_hs, csrrw, hcounteren, hcounteren_write;
endgroup

function void shcounterenw_sample(int hart, int issue, ins_t ins);
    Shcounterenw_cg.sample(ins);
endfunction
