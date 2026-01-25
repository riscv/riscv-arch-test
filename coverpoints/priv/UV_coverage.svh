///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: David_Harris@hmc.edu 12 January 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_UV

covergroup UV_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrname : coverpoint ins.current.insn[31:20] {
        bins vstart = {CSR_VSTART};
        bins vxsat  = {CSR_VXSAT};
        bins vxrm   = {CSR_VXRM};
        bins vcsr   = {CSR_VCSR};
        bins vl     = {CSR_VL};
        bins vtype  = {CSR_VTYPE};
        bins vlenb  = {CSR_VLENB};
    }

    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`XLEN-1] };
    }

    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {CSRRS};
        bins csrrc = {CSRRC};
    }

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }

    cp_uvcsr_access:           cross priv_mode_u, csrname, csraccesses;
    cp_uvcsrwalk:              cross priv_mode_u, csrname, csrop, walking_ones;
    cp_ucsr_from_m:            cross priv_mode_m, csrname, csraccesses;
endgroup

function void uv_sample(int hart, int issue, ins_t ins);
    UV_cg.sample(ins);
endfunction
