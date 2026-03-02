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
        wildcard bins fadd         = {FADD_S};
        wildcard bins fsub         = {FSUB_S};
        wildcard bins fmul         = {FMUL_S};
        wildcard bins fdiv         = {FDIV_S};
        wildcard bins fcvt_s_w     = {FCVT_S_W};
        wildcard bins fcvt_w_s     = {FCVT_W_S};
        `ifdef D_SUPPORTED
            wildcard bins fcvt_s_d     = {FCVT_S_D};
        `endif
        wildcard bins fmadd        = {FMADD_S};
        wildcard bins fsqrt        = {FSQRT_S};
        wildcard bins fsgnj        = {FSGNJ_S};
        wildcard bins feq          = {FEQ_S};
        wildcard bins fmv_x_f      = {FMV_X_S};
        wildcard bins fmv_f_x      = {FMV_S_X};
        wildcard bins fclass       = {FCLASS_S};
        wildcard bins fmin         = {FMIN_S};
        `ifdef ZFA_SUPPORTED
            wildcard bins fli          = {FLI_S};
            wildcard bins fround       = {FROUND_S};
            `ifdef XLEN32
                `ifdef D_SUPPORTED
                    wildcard bins fmvh         = {FMVH_X_D};
                    wildcard bins fmvp         = {FMVP_D_X};
                `endif
            `endif
        `endif
        wildcard bins add          = {ADD};
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
    }
    mstatus_FS: coverpoint ins.prev.csr[12'h300][14:13] {
    }

    // main coverpoints
    cp_fcsr_access:           cross fcsrname, csraccesses, mstatus_FS; // superset of ZicsrF cp_fcsr_access crossing with mstatus.FS
    cp_mstatus_FS_transition: cross instrs, mstatus_FS;
endgroup

function void smf_sample(int hart, int issue, ins_t ins);
    SmF_cg.sample(ins);
      $display("pc: %h, ins: %h, fround: %b %b",
       ins.current.pc_rdata,
       ins.current.insn,
       ins.current.insn[31:20] == 12'b010000000100,
       ins.current.insn[6:0] == 7'b1010011);
    endfunction
