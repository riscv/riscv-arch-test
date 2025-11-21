///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 4 December 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSS
covergroup ExceptionsS_exceptions_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    ecall: coverpoint ins.current.insn {
        bins ecall  = {32'h00000073};
    }
    branch: coverpoint ins.current.insn {
        wildcard bins branch = {32'b???????_?????_?????_???_?????_1100011};
    }
    branches_taken: coverpoint {ins.current.insn[14:12],                                     // funct3
                                ins.current.rs1_val == ins.current.rs2_val,                  // A = B
                                $signed(ins.current.rs1_val) < $signed(ins.current.rs2_val), // A < B (signed)
                                $unsigned(ins.current.rs1_val) < $unsigned(ins.current.rs2_val)} {                 // A < B (unsigned)
        //wildcard bins beq_taken  = {3'b000, 1'b1, 1'b?, 1'b?};
        wildcard bins beq_taken  = {6'b000_1_?_?};
        wildcard bins bne_taken  = {6'b001_0_?_?};
        wildcard bins blt_taken  = {6'b100_?_1_?};
        wildcard bins bge_taken  = {6'b101_?_0_?};
        wildcard bins bltu_taken = {6'b110_?_?_1};
        wildcard bins bgeu_taken = {6'b111_?_?_0};
    }
    branches_nottaken: coverpoint {ins.current.insn[14:12],                                     // funct3
                                   ins.current.rs1_val == ins.current.rs2_val,                  // A == B
                                   $signed(ins.current.rs1_val) < $signed(ins.current.rs2_val), // A < B (signed)
                                   $unsigned(ins.current.rs1_val) < $unsigned(ins.current.rs2_val)} {                 // A < B (unsigned)
        wildcard bins beq_nottaken  = {6'b000_0_?_?};
        wildcard bins bne_nottaken  = {6'b001_1_?_?};
        wildcard bins blt_nottaken  = {6'b100_?_0_?};
        wildcard bins bge_nottaken  = {6'b101_?_1_?};
        wildcard bins bltu_nottaken = {6'b110_?_?_0};
        wildcard bins bgeu_nottaken = {6'b111_?_?_1};
    }
    jal: coverpoint ins.current.insn {
        wildcard bins jal = {32'b????????????????????_?????_1101111};
    }
    jalr: coverpoint ins.current.insn {
        wildcard bins jalr = {32'b????????????_?????_000_?????_1100111};
    }
    csrops: coverpoint ins.current.insn {
        wildcard bins csrrs  = {32'b????????????_?????_010_?????_1110011};
        wildcard bins csrrc  = {32'b????????????_?????_011_?????_1110011};
        wildcard bins csrrsi = {32'b????????????_?????_110_?????_1110011};
        wildcard bins csrrci = {32'b????????????_?????_111_?????_1110011};
    }
    loadops: coverpoint ins.current.insn {
        wildcard bins lw  = {32'b????????????_?????_010_?????_0000011};
        wildcard bins lh  = {32'b????????????_?????_001_?????_0000011};
        wildcard bins lhu = {32'b????????????_?????_101_?????_0000011};
        wildcard bins lb  = {32'b????????????_?????_000_?????_0000011};
        wildcard bins lbu = {32'b????????????_?????_100_?????_0000011};
        `ifdef XLEN64
            wildcard bins ld  = {32'b????????????_?????_011_?????_0000011};
            wildcard bins lwu = {32'b????????????_?????_110_?????_0000011};
        `endif
    }
    storeops: coverpoint ins.current.insn {
        wildcard bins sb = {32'b????????????_?????_000_?????_0100011};
        wildcard bins sh = {32'b????????????_?????_001_?????_0100011};
        wildcard bins sw = {32'b????????????_?????_010_?????_0100011};
        `ifdef XLEN64
            wildcard bins sd = {32'b????????????_?????_011_?????_0100011};
        `endif
    }
    sw_lw: coverpoint ins.current.insn {
        wildcard bins sw   = {32'b????????????_?????_010_?????_0100011};
        wildcard bins lw   = {32'b????????????_?????_010_?????_0000011};
    }
    illegalops: coverpoint ins.current.insn {
        bins zeros = {'0};
        bins ones  = {'1};
    }
    ebreak: coverpoint ins.current.insn {
        bins ebreak = {32'h00100073};
    }
    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0]  {
        // auto fills 000 through 111
    }
    rs1_zero: coverpoint ins.current.insn[19:15] {
        bins zero = {5'b00000};
    }
    seed: coverpoint ins.current.insn[31:20] {
        bins seed = {12'h015};
    }
    csr_0x000: coverpoint ins.current.insn[31:20] {
        bins zero = {12'h000};
    }
    mstatus_MIE: coverpoint ins.prev.csr[12'h300][3] {
        // auto fills 1 and 0
    }
    sstatus_SIE: coverpoint ins.prev.csr[12'h100][1] {
        // auto fills 1 and 0
    }
    pc_bit_1: coverpoint ins.current.pc_rdata[1] {
        bins zero = {0};
    }
    imm_bit_1: coverpoint ins.current.imm[1] {
        bins one = {1};
    }
    offset: coverpoint ins.current.imm[1:0] {
    }
    rs1_1_0: coverpoint ins.current.rs1_val[1:0] {
    }
    illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
        bins illegal = {`ACCESS_FAULT_ADDRESS};
    }
    illegal_address_misaligned: coverpoint ins.current.imm + ins.current.rs1_val {
        bins illegal_misaligned = {`ACCESS_FAULT_ADDRESS + 1}; // One more than the illegal address is both misaligned and illegal
    }
    medeleg_instraccessfault_enabled: coverpoint ins.current.csr[12'h302][1] {
        bins enabled = {1};
    }
    medeleg_b8: coverpoint ins.current.csr[12'h302][8] {
    }
    medeleg_walk: coverpoint ins.current.csr[12'h302] {
        bins zeros                    = {16'b0000_0000_0000_0000};
        `ifndef COVER_ZCA
            bins instrmisaligned_enabled  = {16'b0000_0000_0000_0001};
        `endif
        bins instraccessfault_enabled = {16'b0000_0000_0000_0010};
        bins illegalinstr_enabled     = {16'b0000_0000_0000_0100};
        bins breakpoint_enabled       = {16'b0000_0000_0000_1000};
        bins loadmisaligned_enabled   = {16'b0000_0000_0001_0000};
        bins loadaccessfault_enabled  = {16'b0000_0000_0010_0000};
        bins storemisaligned_enabled  = {16'b0000_0000_0100_0000};
        bins storeaccessfault_enabled = {16'b0000_0000_1000_0000};
        bins ecallu_enabled           = {16'b0000_0001_0000_0000};
        // Delegating ecall to S mode makes it impossible to escape S mode
        // bins ecalls_enabled           = {16'b0000_0010_0000_0000};
        // bit 10 reserved
        // bit 11 is read only zero
        bins instrpagefault_enabled   = {16'b0001_0000_0000_0000};
        bins loadpagefault_enabled    = {16'b0010_0000_0000_0000};
        // bit 14 reserved
        bins storepagefault_enabled   = {16'b1000_0000_0000_0000};
        wildcard bins ones            = {16'b1011_00?1_1111_111?};
    }
    mtvec_stvec_ne: coverpoint {ins.current.csr[12'h305] != ins.current.csr[12'h105]} {
        bins notequal = {1};
    }

    // main coverpoints
    cp_instr_adr_misaligned_branch:          cross branch, branches_taken, pc_bit_1, imm_bit_1, priv_mode_s;
    cp_instr_adr_misaligned_branch_nottaken: cross branch, branches_nottaken, pc_bit_1, imm_bit_1, priv_mode_s;
    cp_instr_adr_misaligned_jal:             cross jal, pc_bit_1, imm_bit_1, priv_mode_s;
    cp_instr_adr_misaligned_jalr:            cross jalr, rs1_1_0, offset, priv_mode_s;
    cp_instr_access_fault:                   cross jalr, illegal_address, priv_mode_s;
    cp_illegal_instruction:                  cross illegalops, priv_mode_s;
    cp_illegal_instruction_seed:             cross csrops, rs1_zero, seed, priv_mode_s;
    cp_illegal_instruction_csr:              cross csrops, csr_0x000, priv_mode_s;
    cp_breakpoint:                           cross ebreak, priv_mode_s;
    cp_load_address_misaligned:              cross loadops, adr_LSBs, priv_mode_s;
    cp_load_access_fault:                    cross loadops, illegal_address, priv_mode_s;
    cp_store_address_misaligned:             cross storeops, adr_LSBs, priv_mode_s;
    cp_store_access_fault:                   cross storeops, illegal_address, priv_mode_s;
    cp_ecall_s:                              cross ecall, priv_mode_s;
    cp_misaligned_priority:                  cross sw_lw, illegal_address_misaligned, priv_mode_s;
    cp_medeleg_msu_instrmisaligned:          cross jalr,     rs1_1_0, offset, priv_mode_msu, medeleg_walk;
    cp_medeleg_msu_loadmisaligned:           cross loadops,    adr_LSBs,         priv_mode_msu, medeleg_walk;
    cp_medeleg_msu_storemisaligned:          cross storeops,   adr_LSBs,         priv_mode_msu, medeleg_walk;
    cp_medeleg_msu_instraccessfault:         cross jalr,       illegal_address,  priv_mode_msu, medeleg_walk;
    cp_medeleg_msu_loadaccessfault:          cross loadops,    illegal_address,  priv_mode_msu, medeleg_walk;
    cp_medeleg_msu_storeaccessfault:         cross storeops,   illegal_address,  priv_mode_msu, medeleg_walk;
    cp_medeleg_msu_illegalinstruction:       cross illegalops,                   priv_mode_msu, medeleg_walk;
    cp_medeleg_msu_ecall:                    cross ecall,                        priv_mode_msu, medeleg_walk;
    cp_medeleg_msu_ebreak:                   cross ebreak,                       priv_mode_msu, medeleg_walk;
    cp_stvec:                                cross jalr, illegal_address, priv_mode_su, medeleg_instraccessfault_enabled, mtvec_stvec_ne; // Testplan was not specific, I chose instr access fault for the delegated exception
    cp_xstatus_ie:                           cross ecall, priv_mode_su, mstatus_MIE, sstatus_SIE, medeleg_b8;

endgroup

function void exceptionss_sample(int hart, int issue, ins_t ins);
    ExceptionsS_exceptions_cg.sample(ins);

// $display("mode: %b, medel: %b, funct3: %b, rs1_1_0: %b, pc_1: %b, offset: %b ",
//     ins.current.mode,
//     ins.current.csr[12'h302],
//     ins.current.insn[14:12],
//     ins.current.rs1_val[1:0],
//     ins.current.pc_rdata[1],
//     ins.current.imm[1:0]);
endfunction
