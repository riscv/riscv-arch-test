///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 24 November 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSZC
covergroup ExceptionsZc_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // building blocks for the main coverpoints
    loadops: coverpoint ins.current.insn {

        wildcard bins c_lw    = {C_LW};
        wildcard bins c_lwsp  = {C_LWSP};
        `ifdef ZCB_SUPPORTED
            wildcard bins c_lh    = {C_LH};
            wildcard bins c_lhu   = {C_LHU};
            wildcard bins c_lbu   = {C_LBU};
        `endif
        `ifdef ZCD_SUPPORTED
            wildcard bins c_fld   = {C_FLD};
            wildcard bins c_fldsp = {C_FLDSP};
        `endif
        `ifdef ZCF_SUPPORTED // UDB_MXLEN_32
            wildcard bins c_flw   = {C_FLW};
            wildcard bins c_flwsp = {C_FLWSP};
        `endif

        `ifdef UDB_MXLEN_64
            wildcard bins c_ld   = {C_LD};
            wildcard bins c_ldsp = {C_LDSP};
        `endif

    }

    storeops: coverpoint ins.current.insn {
        wildcard bins c_sw    = {C_SW};
        wildcard bins c_swsp  = {C_SWSP};
        `ifdef ZCB_SUPPORTED
            wildcard bins c_sb    = {C_SB};
            wildcard bins c_sh    = {C_SH};
        `endif
        `ifdef ZCD_SUPPORTED
            wildcard bins c_fsd   = {C_FSD};
            wildcard bins c_fsdsp = {C_FSDSP};
        `endif
        `ifdef ZCF_SUPPORTED // only supported in UDB_MXLEN_32
            wildcard bins c_fsw   = {C_FSW};
            wildcard bins c_fswsp = {C_FSWSP};
        `endif

        `ifdef UDB_MXLEN_64
            wildcard bins c_sd   = {C_SD};
            wildcard bins c_sdsp = {C_SDSP};
        `endif

    }

    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0]  {
        // auto fills 000 through 111
    }

    // main coverpoints
    cp_breakpoint:                           coverpoint ins.current.insn[15:0] {bins c_ebreak = {16'h9002};}
    cp_load_address_misaligned:              cross loadops, adr_LSBs;
    cp_store_address_misaligned:             cross storeops, adr_LSBs;
    cp_illegal_instruction:                  coverpoint ins.current.insn[15:0] { bins illegal0 = {'0}; }

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        cp_load_access_fault:                    cross loadops, illegal_address;
        cp_store_access_fault:                   cross storeops, illegal_address;
    `endif
endgroup

function void exceptionszc_sample(int hart, int issue, ins_t ins);
    ExceptionsZc_cg.sample(ins);

    //$display("OP: %b, LSB: %b, rs1: %b, SPdata???: %b ", ins.current.insn[15:0], {ins.current.rs1_val + ins.current.imm}[2:0], ins.current.rs1_val, ins.current.x_wdata[2][2:0]);
endfunction
