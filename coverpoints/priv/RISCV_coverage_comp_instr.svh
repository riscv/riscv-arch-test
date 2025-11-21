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
        bins c00[] = {[0:$]};
        // exhaustive test of 2^14 compressed instructions with op=00
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
        bins c10a[] = {[0:14'b0000_1111111111]};
        `ifdef XLEN32
            ignore_bins c_slii_custom = {[14'b0001_0000000000:14'b0001_1111111111]}; // reserved for custom use in RV32Zca; behavior is unpredictable
        `else
            bins c_slli_rv64[] = {[14'b0001_0000000000:14'b0001_1111111111]}; // RV64Zca c.slli with shift amount of 32-63
        `endif
        bins c10b[] = {[14'b001_00000000000:14'b01111111111111]};
        bins illegal_c_jr = {14'b10000000000000}; // illegal for rs1 = 0
        ignore_bins c_jr = {[14'b10000000000001:14'b10001111111111]};
        bins illegal_c_jalr = {14'b10010000000000}; // illegal for rs1 = 0
        ignore_bins c_jalr = {[14'b10010000000001:14'b10011111111111]};
        bins c10c[] = {[14'b10100000000000:$]};
    }
