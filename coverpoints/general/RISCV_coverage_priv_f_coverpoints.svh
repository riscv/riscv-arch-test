///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Floating-point CSR and instruction coverpoints common to Sm_F_cg, S_F_cg, H_F_cg and U_F_cg
//   Coverpoints that name mstatus/sstatus stay in each covergroup.
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

deterministic_instrs: coverpoint ins.current.insn {
    wildcard bins flw          = {FLW};
    wildcard bins fadd         = {FADD_S};
    wildcard bins fsub         = {FSUB_S};
    wildcard bins fmul         = {FMUL_S};
    wildcard bins fdiv         = {FDIV_S};
    wildcard bins fcvt_s_w     = {FCVT_S_W};
    `ifdef D_SUPPORTED
        wildcard bins fcvt_s_d     = {FCVT_S_D};
    `endif
    wildcard bins fmadd        = {FMADD_S};
    wildcard bins fsqrt        = {FSQRT_S};
    wildcard bins fsgnj        = {FSGNJ_S};
    wildcard bins fmv_f_x      = {FMV_S_X};
    wildcard bins fmin         = {FMIN_S};
    wildcard bins fcvt_w_s     = {FCVT_W_S};
    wildcard bins fcvt_wu_s    = {FCVT_WU_S};
    wildcard bins feq          = {FEQ_S};
    `ifdef ZFA_SUPPORTED
        `ifdef D_SUPPORTED
            wildcard bins fcvtmod_w_d  = {FCVTMOD_W_D};
        `endif
        wildcard bins fli          = {FLI_S};
        wildcard bins fround       = {FROUND_S};
        `ifdef UDB_MXLEN_32
            `ifdef D_SUPPORTED
                wildcard bins fmvp         = {FMVP_D_X};
            `endif
        `endif
    `endif
    wildcard bins add          = {ADD};
    wildcard bins csrrw_fcsr   = {CSRRW} iff (ins.current.insn[31:20] == CSR_FCSR);
    wildcard bins csrrw_frm    = {CSRRW} iff (ins.current.insn[31:20] == CSR_FRM);
    wildcard bins csrrw_fflags = {CSRRW} iff (ins.current.insn[31:20] == CSR_FFLAGS);
    wildcard bins csrrs_fcsr   = {CSRRS} iff (ins.current.insn[31:20] == CSR_FCSR);
    wildcard bins csrrs_frm    = {CSRRS} iff (ins.current.insn[31:20] == CSR_FRM);
    wildcard bins csrrs_fflags = {CSRRS} iff (ins.current.insn[31:20] == CSR_FFLAGS);
    wildcard bins csrrc_fcsr   = {CSRRC} iff (ins.current.insn[31:20] == CSR_FCSR);
    wildcard bins csrrc_frm    = {CSRRC} iff (ins.current.insn[31:20] == CSR_FRM);
    wildcard bins csrrc_fflags = {CSRRC} iff (ins.current.insn[31:20] == CSR_FFLAGS);
}
nondeterministic_instrs: coverpoint ins.current.insn {
    wildcard bins fsw          = {FSW};
    wildcard bins fmv_x_f      = {FMV_X_S};
    wildcard bins fclass       = {FCLASS_S};
    `ifdef ZFA_SUPPORTED
        `ifdef UDB_MXLEN_32
            `ifdef D_SUPPORTED
                wildcard bins fmvh         = {FMVH_X_D};
            `endif
        `endif
    `endif
    wildcard bins csrr_fcsr    = {CSRR} iff (ins.current.insn[31:20] == CSR_FCSR);
    wildcard bins csrr_frm     = {CSRR} iff (ins.current.insn[31:20] == CSR_FRM);
    wildcard bins csrr_fflags  = {CSRR} iff (ins.current.insn[31:20] == CSR_FFLAGS);
}
