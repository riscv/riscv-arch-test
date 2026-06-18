///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups Initialization File
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SSCOUNTERENW
covergroup Sscounterenw_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    scounteren_csr: coverpoint ins.current.insn[31:20] {
        wildcard bins scounteren = {CSR_SCOUNTEREN};
    }
    scounteren_ones_zeros: coverpoint ins.current.rs1_val[31:0] {
            bins all_zeros  =   {32'b00000000000000000000000000000000};
            bins all_ones   =   {32'b11111111111111111111111111111111};
    }
    cp_scounteren_writable: cross priv_mode_s, csrrw, scounteren_csr, scounteren_ones_zeros;

endgroup

function void sscounterenw_sample(int hart, int issue, ins_t ins);
    Sscounterenw_cg.sample(ins);
endfunction
