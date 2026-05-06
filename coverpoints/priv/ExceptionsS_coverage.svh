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
covergroup ExceptionsS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    ecall: coverpoint ins.current.insn {
        bins ecall  = {ECALL};
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
        wildcard bins jal = {JAL};
    }
    jalr: coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }
    csrops: coverpoint ins.current.insn {
        wildcard bins csrrs  = {CSRRS};
        wildcard bins csrrc  = {CSRRC};
        wildcard bins csrrsi = {CSRRSI};
        wildcard bins csrrci = {CSRRCI};
    }
    loadops: coverpoint ins.current.insn {
        wildcard bins lw  = {LW};
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lb  = {LB};
        wildcard bins lbu = {LBU};
        `ifdef XLEN64
            wildcard bins ld  = {LD};
            wildcard bins lwu = {LWU};
        `endif
    }
    storeops: coverpoint ins.current.insn {
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef XLEN64
            wildcard bins sd = {SD};
        `endif
    }
    sw_lw: coverpoint ins.current.insn {
        wildcard bins sw   = {SW};
        wildcard bins lw   = {LW};
    }
    illegalops: coverpoint ins.current.insn {
        bins zeros = {'0};
        bins ones  = {'1};
    }
    ebreak: coverpoint ins.current.insn {
        bins ebreak = {EBREAK};
    }
    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0]  {
        // auto fills 000 through 111
    }
    rs1_zero: coverpoint ins.current.insn[19:15] {
        bins zero = {5'b00000};
    }
    seed: coverpoint ins.current.insn[31:20] {
        bins seed = {CSR_SEED};
    }
    csr_0x000: coverpoint ins.current.insn[31:20] {
        bins zero = {12'h000};
    }
    mstatus_MIE: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
        // auto fills 1 and 0
    }
    mstatus_SIE: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
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
    medeleg_illegalinstr_enabled: coverpoint ins.current.csr[CSR_MEDELEG][2] {
        bins enabled = {1};
    }
    medeleg_b8: coverpoint ins.current.csr[CSR_MEDELEG][8] {
    }
    medeleg_walk: coverpoint ins.current.csr[CSR_MEDELEG] {
        bins zeros                    = {16'b0000_0000_0000_0000};
        `ifndef ZCA_SUPPORTED
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
    mtvec_stvec_ne: coverpoint {ins.current.csr[CSR_MTVEC] != ins.current.csr[CSR_STVEC]} {
        bins notequal = {1};
    }

    // main coverpoints
    cp_instr_adr_misaligned_branch:          cross priv_mode_s, branch, branches_taken, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_branch_nottaken: cross priv_mode_s, branch, branches_nottaken, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jal:             cross priv_mode_s, jal, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jalr:            cross priv_mode_s, jalr, rs1_1_0, offset;
    cp_illegal_instruction:                  cross priv_mode_s, illegalops;
    cp_illegal_instruction_seed:             cross priv_mode_s, csrops, rs1_zero, seed;
    cp_illegal_instruction_csr:              cross priv_mode_s, csrops, csr_0x000;
    cp_breakpoint:                           cross priv_mode_s, ebreak;
    cp_load_address_misaligned:              cross priv_mode_s, loadops, adr_LSBs;
    cp_store_address_misaligned:             cross priv_mode_s, storeops, adr_LSBs;
    cp_ecall_s:                              cross priv_mode_s, ecall;
    cp_medeleg_msu_instrmisaligned:          cross priv_mode_m_s_u, jalr,     rs1_1_0, offset, medeleg_walk;
    cp_medeleg_msu_loadmisaligned:           cross priv_mode_m_s_u, loadops,    adr_LSBs,         medeleg_walk;
    cp_medeleg_msu_storemisaligned:          cross priv_mode_m_s_u, storeops,   adr_LSBs,         medeleg_walk;
    cp_medeleg_msu_illegalinstruction:       cross priv_mode_m_s_u, illegalops,                   medeleg_walk;
    cp_medeleg_msu_ecall:                    cross priv_mode_m_s_u, ecall,                        medeleg_walk;
    cp_medeleg_msu_ebreak:                   cross priv_mode_m_s_u, ebreak,                       medeleg_walk;
    cp_stvec:                                cross priv_mode_s_u, illegalops, medeleg_illegalinstr_enabled, mtvec_stvec_ne; // Testplan was not specific, I chose illegal instruction fault for the delegated exception
    cp_xstatus_ie:                           cross priv_mode_s_u, ecall, mstatus_MIE, mstatus_SIE, medeleg_b8;

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        illegal_address_misaligned: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal_misaligned = {`RVMODEL_ACCESS_FAULT_ADDRESS + 1}; // One more than the illegal address is both misaligned and illegal
        }
        cp_instr_access_fault:                   cross priv_mode_s, jalr, illegal_address;
        cp_load_access_fault:                    cross priv_mode_s, loadops, illegal_address;
        cp_store_access_fault:                   cross priv_mode_s, storeops, illegal_address;
        cp_misaligned_priority:                  cross priv_mode_s, sw_lw, illegal_address_misaligned;
        cp_medeleg_msu_instraccessfault:         cross priv_mode_m_s_u, jalr,       illegal_address,  medeleg_walk;
        cp_medeleg_msu_loadaccessfault:          cross priv_mode_m_s_u, loadops,    illegal_address,  medeleg_walk;
        cp_medeleg_msu_storeaccessfault:         cross priv_mode_m_s_u, storeops,   illegal_address,  medeleg_walk;
    `endif

endgroup

function void exceptionss_sample(int hart, int issue, ins_t ins);
    ExceptionsS_cg.sample(ins);

// $display("mode: %b, medel: %b, funct3: %b, rs1_1_0: %b, pc_1: %b, offset: %b ",
//     ins.current.mode,
//     ins.current.csr[CSR_MEDELEG],
//     ins.current.insn[14:12],
//     ins.current.rs1_val[1:0],
//     ins.current.pc_rdata[1],
//     ins.current.imm[1:0]);

endfunction
