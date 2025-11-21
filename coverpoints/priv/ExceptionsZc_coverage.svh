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
covergroup ExceptionsZc_exceptions_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // building blocks for the main coverpoints
    loadops: coverpoint ins.current.insn[15:0] {
        wildcard bins c_lw    = {16'b010_???_???_??_???_00};
        wildcard bins c_lh    = {16'b100001_???_1?_???_00};
        wildcard bins c_lhu   = {16'b100001_???_0?_???_00};
        wildcard bins c_lbu   = {16'b100000_???_??_???_00};
        wildcard bins c_fld   = {16'b001_???_???_??_???_00};
        wildcard bins c_lwsp  = {16'b010_?_?????_?????_10};
        wildcard bins c_fldsp = {16'b001_?_?????_?????_10};

        `ifdef XLEN64
            wildcard bins c_ld   = {16'b011_???_???_??_???_00};
            wildcard bins c_ldsp = {16'b011_?_?????_?????_10};
        `else // XLEN32
            wildcard bins c_flw   = {16'b011_???_???_??_???_00};
            wildcard bins c_flwsp = {16'b011_?_?????_?????_10};
        `endif
    }

    storeops: coverpoint ins.current.insn[15:0] {
        wildcard bins c_sb    = {16'b100010_???_??_???_00};
        wildcard bins c_sh    = {16'b100011_???_0?_???_00};
        wildcard bins c_sw    = {16'b110_???_???_??_???_00};
        wildcard bins c_fsd   = {16'b101_???_???_??_???_00};
        wildcard bins c_swsp  = {16'b110_??????_?????_10};
        wildcard bins c_fsdsp = {16'b101_??????_?????_10};

        `ifdef XLEN64
            wildcard bins c_sd   = {16'b111_???_???_??_???_00};
            wildcard bins c_sdsp = {16'b111_??????_?????_10};
        `else // XLEN32
            wildcard bins c_fsw   = {16'b111_???_???_??_???_00};
            wildcard bins c_fswsp = {16'b111_??????_?????_10};
        `endif
    }

    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0]  {
        // auto fills 000 through 111
    }
    illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
        bins illegal = {`ACCESS_FAULT_ADDRESS};
    }

    // main coverpoints
    cp_breakpoint:                           coverpoint ins.current.insn[15:0] {bins c_ebreak = {16'h9002};}
    cp_load_address_misaligned:              cross loadops, adr_LSBs;
    cp_load_access_fault:                    cross loadops, illegal_address;
    cp_store_address_misaligned:             cross storeops, adr_LSBs;
    cp_store_access_fault:                   cross storeops, illegal_address;

endgroup

function void exceptionszc_sample(int hart, int issue, ins_t ins);
    ExceptionsZc_exceptions_cg.sample(ins);

    //$display("OP: %b, LSB: %b, rs1: %b, SPdata???: %b ", ins.current.insn[15:0], {ins.current.rs1_val + ins.current.imm}[2:0], ins.current.rs1_val, ins.current.x_wdata[2][2:0]);
endfunction
