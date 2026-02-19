///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SMF
covergroup SmF_cg with function sample(ins_t ins);
    option.per_instance = 0;

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

    instrs: coverpoint ins.current.insn {
        wildcard bins fsw          = {FSW};
        wildcard bins flw          = {FLW};
        wildcard bins fadd         = {FADD.S};
        wildcard bins fsub         = {FSUB.S};
        wildcard bins fmul         = {FMUL.S};
        wildcard bins fdiv         = {FDIV.S};
        wildcard bins fcvt_s_w     = {FCVT.S.W};
        wildcard bins fcvt_w_s     = {FCVT.W.S};
        `ifdef D_SUPPORTED
            wildcard bins fcvt_s_d     = {FCVT.S.D};
        `endif
        wildcard bins fmadd        = {FMADD.S};
        wildcard bins fsqrt        = {FSQRT.S};
        wildcard bins fsgnj        = {FSGNJ.S};
        wildcard bins feq          = {FEQ.S};
        wildcard bins fmv_x_f      = {FMV.X.S};
        wildcard bins fmv_f_x      = {FMV.S.X};
        wildcard bins fclass       = {FCLASS.S};
        wildcard bins fmin         = {FMIN.S};
        `ifdef ZFA_SUPPORTED
            wildcard bins fli          = {FLI.S};
            wildcard bins fround       = {FROUND.S};
        `endif
        wildcard bins add          = {32'b0000000_?????_?????_000_?????_0110011};
        wildcard bins csrr_fcsr    = {32'b000000000011_00000_010_?????_1110011};
        wildcard bins csrr_frm     = {32'b000000000010_00000_010_?????_1110011};
        wildcard bins csrr_fflags  = {32'b000000000001_00000_010_?????_1110011};
        wildcard bins csrrw_fcsr   = {32'b000000000011_?????_001_?????_1110011};
        wildcard bins csrrw_frm    = {32'b000000000010_?????_001_?????_1110011};
        wildcard bins csrrw_fflags = {32'b000000000001_?????_001_?????_1110011};
        wildcard bins csrrs_fcsr   = {32'b000000000011_?????_010_?????_1110011};
        wildcard bins csrrs_frm    = {32'b000000000010_?????_010_?????_1110011};
        wildcard bins csrrs_fflags = {32'b000000000001_?????_010_?????_1110011};
        wildcard bins csrrc_fcsr   = {32'b000000000011_?????_011_?????_1110011};
        wildcard bins csrrc_frm    = {32'b000000000010_?????_011_?????_1110011};
        wildcard bins csrrc_fflags = {32'b000000000001_?????_011_?????_1110011};
        `ifdef XLEN32
            `ifdef D_SUPPORTED
                wildcard bins fmvh         = {32'b1110001_00001_?????_000_?????_1010011};
                wildcard bins fmvp         = {32'b1011001_?????_?????_000_?????_1010011};
            `endif
        `endif
    }
    mstatus_FS: coverpoint ins.prev.csr[12'h300][14:13] {
    }

    // main coverpoints
    cp_fcsr_access:           cross fcsrname, csraccesses, mstatus_FS; // superset of ZicsrF cp_fcsr_access crossing with mstatus.FS
    cp_mstatus_FS_transition: cross instrs, mstatus_FS;
endgroup

function void smf_sample(int hart, int issue, ins_t ins);
    SmF_cg.sample(ins);
endfunction
