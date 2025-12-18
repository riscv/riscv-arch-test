///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Standard Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    // helper coverpoints for illegal compressed instruction coverage for the Ssstrict extension

    compressed00 : coverpoint ins.current.insn[15:2] iff (ins.current.insn[1:0] == 2'b00) {
        // exhaustive test of 2^14 compressed instructions with op=00 with following exclusions that would be hard to test
        bins c00a[]       = {[14'b00000000000000:14'b00011111111111]};
        ignore_bins c_fld = {[14'b00100000000000:14'b00111111111111]}; // c.fld throw exceptions for bad addresses
        ignore_bins c_lw  = {[14'b01000000000000:14'b01011111111111]}; // c.lw throw exceptions for bad addresses
        bins c00b[]       = {[14'b01100000000000:14'b01111111111111]};
        ignore_bins c_lbu = {[14'b10000000000000:14'b10000011111111]}; // c.lbu throw exceptions for bad addresses
        ignore_bins c_lh  = {[14'b10000100000000:14'b10000111111111]}; // c.lh throw exceptions for bad addresses
        ignore_bins c_sb  = {[14'b10001000000000:14'b10001111111111]}; // c.sb throw exceptions for bad addresses
        ignore_bins c_sh0 = {[14'b10001100000000:14'b10001100001111]}; // c.sh throw exceptions for bad addresses
        bins c00_0[]      = {[14'b10001100010000:14'b10001100011111]};
        ignore_bins c_sh1 = {[14'b10001100100000:14'b10001100101111]}; // c.sh throw exceptions for bad addresses
        bins c00_1[]      = {[14'b10001100110000:14'b10001100111111]};
        ignore_bins c_sh2 = {[14'b10001101000000:14'b10001101001111]}; // c.sh throw exceptions for bad addresses
        bins c00_2[]      = {[14'b10001101010000:14'b10001101011111]};
        ignore_bins c_sh3 = {[14'b10001101100000:14'b10001101101111]}; // c.sh throw exceptions for bad addresses
        bins c00_3[]      = {[14'b10001101110000:14'b10001101111111]};
        ignore_bins c_sh4 = {[14'b10001110000000:14'b10001110001111]}; // c.sh throw exceptions for bad addresses
        bins c00_4[]      = {[14'b10001110010000:14'b10001110011111]};
        ignore_bins c_sh5 = {[14'b10001110100000:14'b10001110101111]}; // c.sh throw exceptions for bad addresses
        bins c00_5[]      = {[14'b10001110110000:14'b10001110111111]};
        ignore_bins c_sh6 = {[14'b10001111000000:14'b10001111001111]}; // c.sh throw exceptions for bad addresses
        bins c00_6[]      = {[14'b10001111010000:14'b10001111011111]};
        ignore_bins c_sh7 = {[14'b10001111100000:14'b10001111101111]}; // c.sh throw exceptions for bad addresses
        bins c00_7[]      = {[14'b10001111110000:14'b10001111111111]};
        bins c00_c[]      = {[14'b10010000000000:14'b10011111111111]};
        ignore_bins c_fsd = {[14'b10100000000000:14'b10111111111111]}; // c.fsd throw exceptions for bad addresses
        ignore_bins c_sw  = {[14'b11000000000000:14'b11011111111111]}; // c.sw throw exceptions for bad addresses
        bins c00_d        = {[14'b11100000000000:14'b11111111111111]};
    }
    compressed01 : coverpoint ins.current.insn[15:2] iff (ins.current.insn[1:0] == 2'b01) {
        // exhaustive test of 2^14 compressed instructions with op = 01 with following exceptions that would be hard to test
        bins c01[] = {[0:14'b00011111111111]};
        ignore_bins c_jal = {[14'b00100000000000:14'b00111111111111]};
        bins c01b[] = {[14'b01000000000000:14'b10001_111111111]};
        `ifdef XLEN32
            ignore_bins c_srli_srai_custom = {[14'b10010_000000000:14'b10010_111111111]}; // reserved for custom use in RV32Zca; behavior is unpredictable
        `else
            bins c_srli_srai_rv64[] = {[14'b10010_000000000:14'b10010_111111111]}; // RV64Zca c.srli/srai with shift amount of 32-63
        `endif
        bins c01c[] = {[14'b10011_000000000:14'b10011_111111111]};
        ignore_bins c_j = {[14'b10100000000000:14'b10111111111111]};
        ignore_bins c_bez_bez = {[14'b11000000000000:14'b11111111111111]};
     }
    compressed10 : coverpoint ins.current.insn[15:2] iff (ins.current.insn[1:0] == 2'b10) {
        // exhaustive test of 2^14 compressed instructions with op = 10
        //bins c10a[] = {[0:14'b01111111111111]};
        bins c10a[]           = {[0:14'b0000_1111111111]};
        `ifdef XLEN32
            ignore_bins c_slii_custom = {[14'b0001_0000000000:14'b0001_1111111111]}; // reserved for custom use in RV32Zca; behavior is unpredictable
        `else
            bins c_slli_rv64[] = {[14'b0001_0000000000:14'b0001_1111111111]}; // RV64Zca c.slli with shift amount of 32-63
        `endif
        ignore_bins c_fldsp[] = {[14'b001_00000000000:14'b001_11111111111]}; // c.fldsp throws exceptions for bad addresses.
        ignore_bins c_lwsp[]  = {[14'b010_00000000000:14'b010_11111111111]}; // c.lwsp throws exceptions for bad addresses.
        bins c10b[]           = {[14'b011_00000000000:14'b011_11111111111]};
        bins illegal_c_jr     = {14'b10000000000000}; // jr illegal for rs1 = 0
        ignore_bins c_jr      = {[14'b1000_0000000001:14'b1000_1111111111]};   // c.jr causes test program to go to random place.  This ignore excludes some instructions with insn[7:2] != 00000 that ought to be covered.  Including these would be cumbersome and illegalinstrtests.py generates test to hit them anyway, so the coverpoint is written this way for simplicity.
        bins illegal_c_jalr   = {14'b1001_0000000000}; // jalr illegal for rs1 = 0
        ignore_bins c_jalr    = {[14'b1001_0000000001:14'b1001_1111111111]};   // c.jalr.  See c.jr comments above
        ignore_bins c_fsdsp[] = {[14'b101_00000000000:14'b101_11111111111]}; // c.fsdsp throws exceptions for bad addresses.
        ignore_bins c_swsp[]  = {[14'b110_00000000000:14'b110_11111111111]}; // c.swsp throws exceptions for bad addresses.
        bins c10c[]           = {[14'b111_00000000000:14'b111_11111111111]};
    }
