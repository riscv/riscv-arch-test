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

`define COVER_SDTRIGSM
covergroup SdtrigSm_mcontrol6_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // building blocks for the main coverpoints
    triggernum: coverpoint ins.current.csr[CSR_TSELECT] {
        // TODO: restrict to only triggers that support MCONTROL6
        bins all_triggers[] = {[UDB_NUM_TRIGGERS-1:0]};
    }
    mcontrol6_type: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins mcontrol6 = {4'b0110}; // MCONTROL6 has type 6
    }
    dmode_0: coverpoint ins.current.csr[CSR_TDATA1][XLEN-5] {
        bins zero = {1'b0}; // Accessible from machine and debug mode
    }
    action: coverpoint ins.current.csr[CSR_TDATA1][15:12] {
        bins breakpoint = {4'b0000}; // Breakpoint action
    }
    select_adr: coverpoint ins.current.csr[CSR_TDATA1][21] {
        bins adr = {1'b0}; // Select on address match
    }
    select_data: coverpoint ins.current.csr[CSR_TDATA1][21] {
        bins data = {1'b1}; // Select on data match
    }
    size_all: coverpoint ins.current.csr[CSR_TDATA1][18:16] {
        bins size_all = {3'b000}; // Match all sizes
    }
    chain_off: coverpoint ins.current.csr[CSR_TDATA1][11] {
        bins chain_off = {1'b0}; // No chaining
    }
    match_eq: coverpoint ins.current.csr[CSR_TDATA1][10:7] {
        bins eq = {4'b0000};
    }
    uncertainen_0: coverpoint ins.current.csr[CSR_TDATA1][5] {
        bins exact = {1'b0};
    }
    priv_m: coverpoint {ins.current.csr[CSR_TDATA1][6],  // m
                                  ins.current.csr[CSR_TDATA1][4],  // s
                                  ins.current.csr[CSR_TDATA1][3],  // u
                                  ins.current.csr[CSR_TDATA1][24], // vs
                                  ins.current.csr[CSR_TDATA1][23]  // vu
                                  } {
        bins m = {5'b10000}; // machine mode only
    }
    perm_exec: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins exec = {3'b100};
    }
    perm_store: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins store = {3'b010};
    }
    perm_load: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins load = {3'b001};
    }
    mcontrol6_priv_all: coverpoint {ins.current.csr[CSR_TDATA1][6],  // m
                                    ins.current.csr[CSR_TDATA1][4],  // s
                                    ins.current.csr[CSR_TDATA1][3],  // u
                                    ins.current.csr[CSR_TDATA1][24], // vs
                                    ins.current.csr[CSR_TDATA1][23]  // vu
                                   } {
        // all 32 combinations of privilege modes
    }
    dataval: coverpoint ins.current.csr[CSR_TDATA2] {
        bins dataval = {32'hABABBABA}; // Arbitrary value to check tdata2 is being sampled
    }
    store: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }

    mcontrol6: cross mcontrol6_type, dmode_0, action, uncertainen_0;

    // main coverpoints
    cp_sdtrig_mcontrol6_priv_mode:   priv_mode_m, triggernum, dataval, store,
                                     mcontrol, select_data, size_all, chain_off, match_eq, perm_store, priv_all;
    cp_sdtrig_mcontrol6_execute_adr: priv_mode_m, triggernum, tdata2, store,
                                     mcontrol, select_adr, size_all, chain_off, match_eq, perm_exec, priv_m,
                                     tdata2, store;


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
    `endif

endgroup

covergroup SdtrigSm_icount_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
endgroup

function void sdtrigsm_sample(int hart, int issue, ins_t ins);
    SdtrigSm_mcontrol6_cg.sample(ins);
    SdtrigSm_icount_cg.sample(ins);
endfunction
