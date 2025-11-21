///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ENDIANM
covergroup EndianM_endian_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // "Endianness tests in machine mode"

    // building blocks for the main coverpoints
        // ENDIANNESS COVERPOINTS: check writes and reads with various endianness
    cp_sw: coverpoint ins.current.insn {
        wildcard bins sw = {32'b????????????_?????_010_?????_0100011};
    }
    cp_sh: coverpoint ins.current.insn {
        wildcard bins sh = {32'b????????????_?????_001_?????_0100011};
    }
    cp_sb: coverpoint ins.current.insn {
        wildcard bins sb = {32'b????????????_?????_000_?????_0100011};
    }
    cp_lw: coverpoint ins.current.insn {
        wildcard bins lw = {32'b????????????_?????_010_?????_0000011};
    }
    cp_lh: coverpoint ins.current.insn {
        wildcard bins lh = {32'b????????????_?????_001_?????_0000011};
    }
    cp_lhu: coverpoint ins.current.insn {
        wildcard bins lhu = {32'b????????????_?????_101_?????_0000011};
    }
    cp_lb: coverpoint ins.current.insn {
        wildcard bins lb = {32'b????????????_?????_000_?????_0000011};
    }
    cp_lbu: coverpoint ins.current.insn {
        wildcard bins lbu = {32'b????????????_?????_100_?????_0000011};
    }
    cp_byteoffset: coverpoint {ins.current.imm + ins.current.rs1_val}[2:0] {
        // all byte offsets
    }
    cp_halfoffset: coverpoint {ins.current.imm + ins.current.rs1_val}[2:0] {
        wildcard ignore_bins lsb = {3'b??1};
        // all halfword offsets
    }
    cp_wordoffset: coverpoint {ins.current.imm + ins.current.rs1_val}[2:0] {
        wildcard ignore_bins b0 = {3'b??1};
        wildcard ignore_bins b2 = {3'b?1?};
        // all word offsets
    }
    `ifdef XLEN64
        mstatus_mbe: coverpoint ins.current.csr[12'h300][37] { // mbe is mstatus[37] in RV64
        }
    `else
        mstatus_mbe: coverpoint ins.current.csr[12'h310][5] { // mbe is mstatush[5] in RV32
        }
    `endif
    // main coverpoints
    cp_mstatus_mbe_endianness_sw: cross priv_mode_m, mstatus_mbe, cp_sw, cp_wordoffset;
    cp_mstatus_mbe_endianness_sh: cross priv_mode_m, mstatus_mbe, cp_sh, cp_halfoffset;
    cp_mstatus_mbe_endianness_sb: cross priv_mode_m, mstatus_mbe, cp_sb, cp_byteoffset;
    cp_mstatus_mbe_endianness_lw: cross priv_mode_m, mstatus_mbe, cp_lw, cp_wordoffset;
    cp_mstatus_mbe_endianness_lh: cross priv_mode_m, mstatus_mbe, cp_lh, cp_halfoffset;
    cp_mstatus_mbe_endianness_lb: cross priv_mode_m, mstatus_mbe, cp_lb, cp_byteoffset;
    cp_mstatus_mbe_endianness_lhu: cross priv_mode_m, mstatus_mbe, cp_lhu, cp_halfoffset;
    cp_mstatus_mbe_endianness_lbu: cross priv_mode_m, mstatus_mbe, cp_lbu, cp_byteoffset;

    `ifdef XLEN64
        cp_sd: coverpoint ins.current.insn {
            wildcard bins sd = {32'b????????????_?????_011_?????_0100011};
        }
        cp_ld: coverpoint ins.current.insn {
            wildcard bins ld = {32'b????????????_?????_001_?????_0000011};
        }
        cp_lwu: coverpoint ins.current.insn {
            wildcard bins lwu = {32'b????????????_?????_110_?????_0000011};
        }
        cp_doubleoffset: coverpoint ins.current.imm[2:0] iff (ins.current.rs1_val[2:0] == 3'b000)  {
            bins zero = {3'b000};
        }
        cp_mstatus_mbe_endianness_sd: cross priv_mode_m, mstatus_mbe, cp_sd, cp_doubleoffset;
        cp_mstatus_mbe_endianness_ld: cross priv_mode_m, mstatus_mbe, cp_ld, cp_doubleoffset;
        cp_mstatus_mbe_endianness_lwu: cross priv_mode_m, mstatus_mbe, cp_lwu, cp_wordoffset;
    `endif

endgroup

function void endianm_sample(int hart, int issue, ins_t ins);
    EndianM_endian_cg.sample(ins);
endfunction
