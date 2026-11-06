///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Floating-point CSR access coverpoints common to Sm_F_cg, S_F_cg, H_F_cg and U_F_cg
//
///////////////////////////////////////////

// building blocks for the main coverpoints
fcsrname : coverpoint ins.current.insn[31:20] {
    bins fcsr    = {CSR_FCSR};
    bins frm     = {CSR_FRM};
    bins fflags  = {CSR_FFLAGS};
}

csraccesses : coverpoint ins.current.insn {
    wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
    wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
    wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
    wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
    wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
}
