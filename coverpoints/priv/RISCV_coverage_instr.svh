///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Standard Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    // helper coverpoints for illegal instruction coverage for the Ssstrict extension

    illegal : coverpoint ins.current.insn { // illegal in RVA22S64; will trap if not in an implemented extension
        // wildcard bins op2  = {32'b?????????????????????????_0001011}; // unused ops custom-0
        wildcard bins op7  = {32'b?????????????????????????_0011111}; // unused ops, reserved for 48-bit
        // wildcard bins op10 = {32'b?????????????????????????_0101011}; // unused ops custom-1
        wildcard bins op15 = {32'b?????????????????????????_0111111}; // unused ops, reserved for 64-bit
        wildcard bins op21 = {32'b?????????????????????????_1010111}; // vector ops
        // wildcard bins op22 = {32'b?????????????????????????_1011011}; // unused ops custom-2/rv128
        wildcard bins op23 = {32'b?????????????????????????_1011111}; // unused ops, reserved for 48-bit
        wildcard bins op26 = {32'b?????????????????????????_1101011}; // reserved
        wildcard bins op29 = {32'b?????????????????????????_1110111}; // VE vector ops
        // wildcard bins op30 = {32'b?????????????????????????_1111011}; // unused ops custom-2/rv128
        wildcard bins op31 = {32'b?????????????????????????_1111111}; // unused ops, reserved for 80+ bit
    }
    // Loads op = 0000011
    load : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b0000011) {
        // Check all 8 types of loads, some illegal in rv32/always
    }
    // FP Loads op = 0000111
    fload : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b0000111) {
        // Check all 8 types of fp Loads, some illegal in various combinations of F/D/Q/Zfh
    }
    // fences/cbo op = 0001111
    fence_cbo : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b0001111) {
        // Check all 8 types of fences: 3-7 should be illegal
    }
    // cbo immediate
    cbo_immediate : coverpoint ins.current.insn[31:20] iff (ins.current.insn[6:0] == 7'b0001111 & ins.current.insn[11:7] == 5'b000 & ins.current.insn[14:12] == 3'b010) {
        // check all 2^12 types of cbo; only 0, 1, 2, and 4 should be legal
    }
    cbo_rd : coverpoint ins.current.insn[11:7] iff (ins.current.insn[6:0] == 7'b0001111 & ins.current.insn[14:12] == 3'b010) {
        // check all 2^5 rd for cbo instructions; only 0 should be legal
    }
    // I-type instructions
    Itype : coverpoint {ins.current.insn[14], ins.current.insn[31:20]} iff (ins.current.insn[6:0] == 7'b0010011 & ins.current.insn[13:12] == 2'b01) {
        // Exhaustive test of 2 * 2^12 complicated bins for I-type instructions with op = 00100011 and funct3 = 1 or 5, and any imm_11:0
        // includes integer shifts, Zbb, Zbs, Zbkb, Zknd, Zkne, Zknh
    }
    Itypef3 :  coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b0010011) {
        // exhaustively cover all 8 funct3 fields of I-type instructions
    }
    aes64ks1i : coverpoint ins.current.insn[24:20] iff (ins.current.insn[6:0] == 7'b0010011 & ins.current.insn[14:12] == 3'b001 & ins.current.insn[31:25] == 7'b0011000) {
        // Exhaustively cover all rs2 fields of aes64ks1i to exercise illegal bit 4 or rnum
    }

    // RV64IW instruction space: op = 0011011
    IWtype : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b0011011) {
        // exercise all 8 bins.  All are illegal in rv32
        // bin 0 is legal addiw in RV64I
        // bins 1 and 5 has some legal funct values
    }
    // RV64IW shifts with op = 001101, funct3 = 1 or 5
    IWshift : coverpoint {ins.current.insn[14], ins.current.insn[31:25]} iff (ins.current.insn[6:0] == 7'b0011011 & ins.current.insn[13:12] == 2'b01) {
        // exercise all 2 * 128 bins of funct7 for funct3 = 1/5
    }
    // Stores op = 0100011
    store : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b0100011) {
        // Check all 8 types of stores, some illegal in rv32/always
    }
    // FP Loads op = 0100111
    fstore : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b0100111) {
        // Check all 8 types of fp stores, some illegal in various combinations of F/D/Q/Zfh
    }
    // Atomic op = 0101111
    atomic_funct3 : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b0101111) {
        // Check all 8 types of atomic funct3; only funct3 = 2 is legal, and only when A supported
    }
    atomic_funct7 : coverpoint {ins.current.insn[12], ins.current.insn[31:27]} iff (ins.current.insn[6:0] == 7'b0101111 & ins.current.insn[14:13] == 3'b01) {
        // Check all 2 flavors (w/d) * 32 flavors of atomics
    }
    lrsc : coverpoint {ins.current.insn[12], ins.current.insn[24:20]} iff (ins.current.insn[6:0] == 7'b0101111 & ins.current.insn[14:13] == 2'b01 & ins.current.insn[31:27] == 5'b00010) {
        // Check all 2 flavors (w/d) * 2^5 rd values; only rs2 = 0 should be legal
    }
    // R-type op = 0110011
    Rtype : coverpoint {ins.current.insn[14:12], ins.current.insn[31:25]} iff (ins.current.insn[6:0] == 7'b0110011) {
        // Exhaustive test of 2^3 * 2^7 complicated bins for R-type instructions
        // includes I, M, Zb*, Zicond, Zbkb, Zknd, Zkne, Zknh
    }
    // RW-type op = 0111011
    RWtype : coverpoint {ins.current.insn[14:12], ins.current.insn[31:25]} iff (ins.current.insn[6:0] == 7'b0111011) {
        // Exhaustive test of 2^3 * 2^7 complicated bins for RW-type instructions
        // includes RV64IW, Zext.h
    }
    // Float op = 1010011
    Ftype : coverpoint {ins.current.insn[14:12], ins.current.insn[31:27]} iff (ins.current.insn[6:0] == 7'b1010011) {
        // Exhaustive test of 2^3 * 2^5 complicated bins for floating-point instructions
        // including illegal functions and illegal rounding modes (5/6)
    }
    fsqrt : coverpoint ins.current.insn[24:20] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b01011) {
        // Exhaustive test of 2^5 encodings; only 00000 is legal
    }
    fclass : coverpoint ins.current.insn[24:20] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11100 & ins.current.insn[14:12] == 3'b001) {
        // Exhaustive test of 2^5 encodings; only 00000 is legal
    }
    fcvtif : coverpoint ins.current.insn[24:22] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11000) {
        // Exhaustive test of 2^3 encodings; only 000 is legal
    }
    fcvtif_fmt : coverpoint {ins.current.insn[26:25], ins.current.insn[21:20]} iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11000 & ins.current.insn[24:22] == 3'b000) {
        // Exhaustive test of 2^4 encodings of formats
    }
    fcvtfi : coverpoint ins.current.insn[24:22] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11010) {
        // Exhaustive test of 2^3 encodings; only 000 is legal
    }
    fcvtfi_fmt : coverpoint {ins.current.insn[26:25], ins.current.insn[21:20]} iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11010 & ins.current.insn[24:22] == 3'b000) {
        // Exhaustive test of 2^4 encodings of formats
    }
    fcvtff : coverpoint ins.current.insn[24:22] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b01000) {
        // Exhaustive test of 2^3 encodings; only 000 is legal
    }
    fcvtff_fmt : coverpoint {ins.current.insn[26:25], ins.current.insn[24:20]} iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b01000) {
        // Exhaustive test of 2^7 encodings; only rs2 = 00000, 00100, 00101 are legal fcvt, fround
    }
    fmvif : coverpoint ins.current.insn[26:20] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11100 & ins.current.insn[14:12] == 3'b000) {
        // Exhaustive test of 2^2 formats * 2^5 encodings; only 00000 is legal
    }
    fmvfi : coverpoint ins.current.insn[26:20] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11110 & ins.current.insn[14:12] == 3'b000) {
        // Exhaustive test of 2^2 formats * 2^5 encodings; only rs2 = 00000 is legal
    }
    fli : coverpoint ins.current.insn[26:20] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11110 & ins.current.insn[14:12] == 3'b000) {
        // Exhaustive test of 2^2 formats * 2^5 encodings; only rs2 = 00001 is legal
    }
    fmvh : coverpoint ins.current.insn[26:20] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11100 & ins.current.insn[14:12] == 3'b000) {
        // Exhaustive test of 2^2 formats * 2^5 encodings; only rs2 = 00001 is possibly legal
    }
    fmvp : coverpoint ins.current.insn[26:25] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11100 & ins.current.insn[14:12] == 3'b000) {
        // Exhaustive test of 4 encodings; only 01 and 11 are possibly legal
    }
    cvtmodwd : coverpoint ins.current.insn[26:20] iff (ins.current.insn[6:0] == 7'b1010011 & ins.current.insn[31:27] == 5'b11000 & ins.current.insn[14:12] == 3'b001) {
        // Exhaustive test of 2^2 formats * 2^5 encodings; only rs2 = 00001 is possibly legal
    }
    // Branches: op = 1100011
    branch : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1100011) {
        // Check all 8 types of branches: 2 & 3 illegal
    }
    // JALRs: op = 1100111
    jalr : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1100111) {
        // test all 8 funct3 codes; only 000 should be legal
    }
    // privileged: op = 1110011
    privileged_funct3 : coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011 & ins.current.insn[19:15] == 5'b00000 & ins.current.insn[11:7] == 5'b00000) {
        // check all 8 types of privileged with rs1 = rd = 0; funct3 = 100 should be illegal
    }
    // focus on funct3 = 0; others are covered by csr tests
    privileged_000 : coverpoint ins.current.insn[31:20] iff (ins.current.insn[6:0] == 7'b1110011 & ins.current.insn[14:12] == 3'b000 & ins.current.insn[19:15] == 5'b00000 & ins.current.insn[11:7] == 5'b00000) {
        // Exhaustive test of 2^12 encodings, only a few are legal
        wildcard ignore_bins custom = {12'b1???11??????}; // custom System instructions don't need checking
    }
    // if funct3 = 0, rd must be 0
    privileged_rd : coverpoint ins.current.insn[11:7] iff (ins.current.insn[6:0] == 7'b1110011 & ins.current.insn[14:12] == 3'b000) {
        // Exhaustive test of 2^5 rd values, only 00000 is legal
    }
    // if funct3 = 0, rs2 must be 0
    privileged_rs2 : coverpoint ins.current.insn[24:20] iff (ins.current.insn[6:0] == 7'b1110011 & ins.current.insn[14:12] == 3'b000) {
        // Exhaustive test of 2^5 rs2 values, only 00000 is legal except on sfence.vma
    }
    reserved : coverpoint ins.current.insn { // reserved but not illegal
        wildcard bins reserved_fence_fm  = {32'b0001_00000000_?????_000_?????_0001111}; // fence with reserved fm
        wildcard bins reserved_fence_tso = {32'b1000_00000000_?????_000_?????_0001111}; // fence.tso with reserved ordering
        wildcard bins reserved_fence_rs1 = {32'b0000_11111111_00001_000_?????_0001111}; // fence with reserved rs1
        wildcard bins reserved_fence_rd  = {32'b0000_11111111_?????_000_00001_0001111}; // fence with reserved rd
        wildcard bins reserved_rm5_fmadd = {32'b???????_?????_?????_101_?????_1000011}; // fma with reserved rm
        wildcard bins reserved_rm6_fmadd = {32'b???????_?????_?????_110_?????_1000011}; // fma with reserved rm
        wildcard bins reserved_rm5_fmsub = {32'b???????_?????_?????_101_?????_1000111}; // fma with reserved rm
        wildcard bins reserved_rm6_fmsub = {32'b???????_?????_?????_110_?????_1000111}; // fma with reserved rm
        wildcard bins reserved_rm5_fnmadd = {32'b???????_?????_?????_101_?????_1001011}; // fma with reserved rm
        wildcard bins reserved_rm6_fnmadd = {32'b???????_?????_?????_110_?????_1001011}; // fma with reserved rm
        wildcard bins reserved_rm5_fnmsub = {32'b???????_?????_?????_101_?????_1001111}; // fma with reserved rm
        wildcard bins reserved_rm6_fnmsub = {32'b???????_?????_?????_110_?????_1001111}; // fma with reserved rm
    }
