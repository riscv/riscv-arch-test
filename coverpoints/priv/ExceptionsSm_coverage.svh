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
        `ifdef UDB_MXLEN_64
            wildcard bins ld  = {LD};
            wildcard bins lwu = {LWU};
        `endif
    }
    storeops: coverpoint ins.current.insn {
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
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
        bins seed = {CSR_SEED};
    }
    mstatus_MIE: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
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
    `ifdef S_SUPPORTED
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
        mstatus_SIE: coverpoint ins.prev.csr[CSR_MSTATUS][1] {
            // auto fills 1 and 0
        }
        medeleg_b8: coverpoint ins.current.csr[CSR_MEDELEG][8] {
            // auto fills 1 and 0: ecall from U-mode delegated to S-mode or not
        }
        jalr_target_bit1: coverpoint {ins.current.rs1_val + ins.current.imm}[1] {
            bins aligned    = {0};  // 4-byte aligned target
            bins misaligned = {1};  // bit 1 set: instruction address misaligned (a legal target with Zca)
        }
    `endif

    // main coverpoints
    cp_instr_adr_misaligned_branch:          cross priv_mode_m, branch, branches_taken, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_branch_nottaken: cross priv_mode_m, branch, branches_nottaken, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jal:             cross priv_mode_m, jal, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jalr:            cross priv_mode_m, jalr, rs1_1_0, offset;
    cp_illegal_instruction:                  cross priv_mode_m, illegalops;
    cp_illegal_instruction_seed:             cross priv_mode_m, csrops, rs1_zero, seed;
    cp_breakpoint:                           cross priv_mode_m, ebreak;
    cp_load_address_misaligned:              cross priv_mode_m, loadops, adr_LSBs;
    cp_store_address_misaligned:             cross priv_mode_m, storeops, adr_LSBs;
    cp_ecall_m:                              cross priv_mode_m, ecall;
    cp_mstatus_ie:                           cross priv_mode_m, ecall, mstatus_MIE;
    `ifdef S_SUPPORTED
        cp_medeleg_msu_instrmisaligned:      cross priv_mode_m_s_u, jalr,       jalr_target_bit1, medeleg_walk;
        cp_medeleg_msu_loadmisaligned:       cross priv_mode_m_s_u, loadops,    adr_LSBs,         medeleg_walk;
        cp_medeleg_msu_storemisaligned:      cross priv_mode_m_s_u, storeops,   adr_LSBs,         medeleg_walk;
        cp_medeleg_msu_illegalinstruction:   cross priv_mode_m_s_u, illegalops,                   medeleg_walk;
        cp_medeleg_msu_ecall:                cross priv_mode_m_s_u, ecall,                        medeleg_walk;
        cp_medeleg_msu_ebreak:               cross priv_mode_m_s_u, ebreak,                       medeleg_walk;
        cp_xstatus_ie:                       cross priv_mode_s_u, ecall, mstatus_MIE, mstatus_SIE, medeleg_b8;
    `endif

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        illegal_address_priority: coverpoint {{ins.current.imm + ins.current.rs1_val}[`UDB_MXLEN-1:3], 3'b000} {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        i_phys_adr_misaligned: coverpoint {ins.current.imm + ins.current.rs1_val}[1:0] {
            bins aligned    = {2'b00};
            bins misaligned = {2'b10};
        }
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            i_phys_address_nonexistent: coverpoint ({{ins.current.imm + ins.current.rs1_val}[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            i_phys_address_nonexistent: coverpoint ({{ins.current.imm + ins.current.rs1_val}[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_instr_access_fault:                   cross priv_mode_m, jalr, illegal_address;
        cp_load_access_fault:                    cross priv_mode_m, loadops, illegal_address;
        cp_store_access_fault:                   cross priv_mode_m, storeops, illegal_address;
        cp_misaligned_priority_fetch:            cross priv_mode_m, i_phys_adr_misaligned, i_phys_address_nonexistent, jalr;
        cp_misaligned_priority_load:             cross priv_mode_m, loadops, adr_LSBs, illegal_address_priority;
        cp_misaligned_priority_store:            cross priv_mode_m, storeops, adr_LSBs, illegal_address_priority;
        `ifdef S_SUPPORTED
            cp_medeleg_msu_instraccessfault:         cross priv_mode_m_s_u, jalr,       illegal_address,  medeleg_walk;
            cp_medeleg_msu_loadaccessfault:          cross priv_mode_m_s_u, loadops,    illegal_address,  medeleg_walk;
            cp_medeleg_msu_storeaccessfault:         cross priv_mode_m_s_u, storeops,   illegal_address,  medeleg_walk;
        `endif
    `endif

endgroup


function void exceptionssm_sample(int hart, int issue, ins_t ins);
    ExceptionsSm_cg.sample(ins);
endfunction
