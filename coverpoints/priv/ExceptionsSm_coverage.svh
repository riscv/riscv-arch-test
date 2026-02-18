///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 18 November 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSSM
covergroup ExceptionsSm_cg with function sample(ins_t ins);
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
            wildcard bins ld  = {32'b????????????_?????_001_?????_0000011};
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
    mstatus_MIE: coverpoint ins.prev.csr[12'h300][3] {
        // auto fills 1 and 0
    }
    pc_bit_1: coverpoint ins.current.pc_rdata[1] {
        bins zero = {0};
    }
    imm_bit_1: coverpoint ins.current.imm[1] {
        bins one = {'1};
    }
    offset: coverpoint ins.current.imm[1:0] {
    }
    rs1_1_0: coverpoint ins.current.rs1_val[1:0] {
    }
    illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
        bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }
    illegal_address_priority: coverpoint {{ins.current.imm + ins.current.rs1_val}[XLEN-1:3], 3'b000} {
        bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }
    i_phys_adr_misaligned: coverpoint ins.current.phys_adr_i[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    `ifdef XLEN64 // Number of physical address bits is different by XLEN, either 34 or 56
        i_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_i[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
            // auto fill 1/0 for the physical address being valid
        }
    `else
        i_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_i[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
            // auto fill 1/0 for the physical address being valid
        }
    `endif

    // main coverpoints
    cp_instr_adr_misaligned_branch:          cross priv_mode_m, branch, branches_taken, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_branch_nottaken: cross priv_mode_m, branch, branches_nottaken, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jal:             cross priv_mode_m, jal, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jalr:            cross priv_mode_m, jalr, rs1_1_0, offset;
    cp_instr_access_fault:                   cross priv_mode_m, jalr, illegal_address;
    cp_illegal_instruction:                  cross priv_mode_m, illegalops;
    cp_illegal_instruction_seed:             cross priv_mode_m, csrops, rs1_zero, seed;
    cp_breakpoint:                           cross priv_mode_m, ebreak;
    cp_load_address_misaligned:              cross priv_mode_m, loadops, adr_LSBs;
    cp_load_access_fault:                    cross priv_mode_m, loadops, illegal_address;
    cp_store_address_misaligned:             cross priv_mode_m, storeops, adr_LSBs;
    cp_store_access_fault:                   cross priv_mode_m, storeops, illegal_address;
    cp_ecall_m:                              cross priv_mode_m, ecall;
    cp_misaligned_priority_fetch:            cross priv_mode_m, i_phys_adr_misaligned, i_phys_address_nonexistent, jalr;
    cp_misaligned_priority_load:             cross priv_mode_m, loadops, adr_LSBs, illegal_address_priority;
    cp_misaligned_priority_store:            cross priv_mode_m, storeops, adr_LSBs, illegal_address_priority;
    cp_mstatus_ie:                           cross priv_mode_m, ecall, mstatus_MIE;
endgroup


function void exceptionssm_sample(int hart, int issue, ins_t ins);
    ExceptionsSm_cg.sample(ins);
endfunction
