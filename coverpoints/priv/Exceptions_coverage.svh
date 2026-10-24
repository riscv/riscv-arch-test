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

`define COVER_EXCEPTIONS

`ifdef ZICBOM_SUPPORTED
    `define EXCEPTIONS_ZICBO_ANY
`elsif ZICBOZ_SUPPORTED
    `define EXCEPTIONS_ZICBO_ANY
`elsif ZICBOP_SUPPORTED
    `define EXCEPTIONS_ZICBO_ANY
`endif

`ifdef F_SUPPORTED
covergroup Exceptions_F_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // building blocks for the main coverpoints
    mstatus_FS_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs")[1:0] {
        bins disabled = {2'b00};
    }
    mstatus_FS_status: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs")[1:0] {
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins fs_initial = {2'b01};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins fs_clean   = {2'b10};
        `endif
        bins fs_dirty   = {2'b11};
    }
    frm_legal: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm")[2:0] {
        bins legal_frm = {3'b000, 3'b001, 3'b010, 3'b011, 3'b100};
    }
    instrs: coverpoint ins.current.insn {
        wildcard bins fsw          = {FSW};
        wildcard bins flw          = {FLW};
        wildcard bins fadd         = {FADD_S};
        wildcard bins fsub         = {FSUB_S};
        wildcard bins fmul         = {FMUL_S};
        wildcard bins fdiv         = {FDIV_S};
        wildcard bins fcvt_x_f     = {FCVT_W_S};
        wildcard bins fcvt_f_x     = {FCVT_S_W};
        `ifdef D_SUPPORTED
            wildcard bins fcvt_f_f     = {FCVT_S_D};
        `endif
        wildcard bins fmadd        = {FMADD_S};
        wildcard bins fsqrt        = {FSQRT_S};
        wildcard bins fsgnj        = {FSGNJ_S};
        wildcard bins feq          = {FEQ_S};
        wildcard bins fmv_x_f      = {FMV_X_S};
        wildcard bins fmv_f_x      = {FMV_S_X};
        wildcard bins fclass       = {FCLASS_S};
        wildcard bins fmin         = {FMIN_S};
        `ifdef ZFA_SUPPORTED
            wildcard bins fli          = {FLI_S};
            wildcard bins fround       = {FROUND_S};
            `ifdef UDB_MXLEN_32
                `ifdef D_SUPPORTED
                    wildcard bins fmvh         = {FMVH_X_D};
                    wildcard bins fmvp         = {FMVP_D_X};
                `endif
            `endif
        `endif
    }
    csr_accesses: coverpoint ins.current.insn {
        wildcard bins csrrw_fcsr   = {CSRRW} iff (ins.current.insn[31:20] == CSR_FCSR);
        wildcard bins csrrw_frm    = {CSRRW} iff (ins.current.insn[31:20] == CSR_FRM);
        wildcard bins csrrw_fflags = {CSRRW} iff (ins.current.insn[31:20] == CSR_FFLAGS);
        wildcard bins csrrs_fcsr   = {CSRRS} iff (ins.current.insn[31:20] == CSR_FCSR);
        wildcard bins csrrs_frm    = {CSRRS} iff (ins.current.insn[31:20] == CSR_FRM);
        wildcard bins csrrs_fflags = {CSRRS} iff (ins.current.insn[31:20] == CSR_FFLAGS);
        wildcard bins csrrc_fcsr   = {CSRRC} iff (ins.current.insn[31:20] == CSR_FCSR);
        wildcard bins csrrc_frm    = {CSRRC} iff (ins.current.insn[31:20] == CSR_FRM);
        wildcard bins csrrc_fflags = {CSRRC} iff (ins.current.insn[31:20] == CSR_FFLAGS);
    }
    loadops: coverpoint ins.current.insn {
        wildcard bins flw = {FLW};
        `ifdef ZFHMIN_SUPPORTED
            wildcard bins flh = {FLH};
        `endif
        `ifdef D_SUPPORTED
            wildcard bins fld = {FLD};
        `endif
        `ifdef Q_SUPPORTED
            wildcard bins flq = {FLQ};
        `endif
    }
    storeops: coverpoint ins.current.insn {
        wildcard bins fsw = {FSW};
        `ifdef ZFHMIN_SUPPORTED
            wildcard bins fsh = {FSH};
        `endif
        `ifdef D_SUPPORTED
            wildcard bins fsd = {FSD};
        `endif
        `ifdef Q_SUPPORTED
            wildcard bins fsq = {FSQ};
        `endif
    }
    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[3:0]  {
        // auto fills 0000 through 1111
    }


    // main coverpoints
    cp_mstatus_fs_illegal_instr: cross instrs, mstatus_FS_zero;
    cp_mstatus_fs_csr_access:    cross csr_accesses, mstatus_FS_zero;
    cp_mstatus_fs_legal:         cross instrs, mstatus_FS_status, frm_legal;
    cp_load_address_misaligned:  cross loadops, adr_LSBs;
    cp_store_address_misaligned: cross storeops, adr_LSBs;

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        cp_load_access_fault:        cross loadops, illegal_address;
        cp_store_access_fault:       cross storeops, illegal_address;
    `endif
endgroup

`endif // F_SUPPORTED

`ifdef S_SUPPORTED
covergroup Exceptions_S_cg with function sample(ins_t ins);
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
    `ifdef ZIBI_SUPPORTED
        zibi_branches_taken: coverpoint {ins.current.insn[6:0], ins.current.insn[14:12],
                                         ins.current.rs1_val == ins.current.imm2} {
            bins beqi_taken = {11'b1100011_010_1};
            bins bnei_taken = {11'b1100011_011_0};
        }
        zibi_branches_nottaken: coverpoint {ins.current.insn[6:0], ins.current.insn[14:12],
                                            ins.current.rs1_val == ins.current.imm2} {
            bins beqi_nottaken = {11'b1100011_010_0};
            bins bnei_nottaken = {11'b1100011_011_1};
        }
    `endif
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
    sw_lw_jalr: coverpoint ins.current.insn {
        wildcard bins sw   = {SW};
        wildcard bins lw   = {LW};
        wildcard bins jalr = {JALR};
    }
    illegalops: coverpoint ins.current.insn {
        bins zeros = {'0};
        bins ones  = {'1};
    }
    ebreak: coverpoint ins.current.insn {
        bins ebreak = {EBREAK};
    }
    `ifdef ZCA_SUPPORTED
        // 32-bit ebreak at 62 mod 64: the fetch straddles a 64-byte boundary. xtval must still
        // be zero or the address of the ebreak, never the address of the second half of the fetch.
        straddle64: coverpoint ins.current.pc_rdata[5:1] {
            bins straddle64 = {5'b11111};
        }
    `endif
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
    mstatus_MIE: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
        // auto fills 1 and 0
    }
    mstatus_SIE: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0] {
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
    medeleg_illegalinstr_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "medeleg", "medeleg")[2] {
        bins enabled = {1};
    }
    mtvec_stvec_ne: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtvec", "mtvec") != get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stvec", "stvec")} {
        bins notequal = {1};
    }

    // main coverpoints
    cp_instr_adr_misaligned_branch:          cross priv_mode_s, branch, branches_taken, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_branch_nottaken: cross priv_mode_s, branch, branches_nottaken, pc_bit_1, imm_bit_1;
    `ifdef ZIBI_SUPPORTED
        cp_instr_adr_misaligned_zibi_branch:          cross priv_mode_s, zibi_branches_taken, pc_bit_1, imm_bit_1;
        cp_instr_adr_misaligned_zibi_branch_nottaken: cross priv_mode_s, zibi_branches_nottaken, pc_bit_1, imm_bit_1;
    `endif
    cp_instr_adr_misaligned_jal:             cross priv_mode_s, jal, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jalr:            cross priv_mode_s, jalr, rs1_1_0, offset;
    cp_illegal_instruction:                  cross priv_mode_s, illegalops;
    cp_illegal_instruction_seed:             cross priv_mode_s, csrops, rs1_zero, seed;
    cp_illegal_instruction_csr:              cross priv_mode_s, csrops, csr_0x000;
    cp_breakpoint:                           cross priv_mode_s, ebreak;
    `ifdef ZCA_SUPPORTED
        cp_ebreak_straddle64:                cross priv_mode_s, ebreak, straddle64;
    `endif
    cp_load_address_misaligned:              cross priv_mode_s, loadops, adr_LSBs;
    cp_store_address_misaligned:             cross priv_mode_s, storeops, adr_LSBs;
    cp_ecall_s:                              cross priv_mode_s, ecall;
    cp_stvec:                                cross priv_mode_s_u, illegalops, medeleg_illegalinstr_enabled, mtvec_stvec_ne; // Testplan was not specific, I chose illegal instruction fault for the delegated exception
    cp_xstatus_ie:                           cross priv_mode_s_u, ecall, mstatus_MIE, mstatus_SIE;

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        illegal_address_misaligned: coverpoint ins.current.imm + ins.current.rs1_val {
            // Both misaligned and illegal: +1 for lw/sw; +2 for jalr, which clears bit 0 of the target
            bins illegal_misaligned = {`RVMODEL_ACCESS_FAULT_ADDRESS + 1, `RVMODEL_ACCESS_FAULT_ADDRESS + 2};
        }
        cp_instr_access_fault:                   cross priv_mode_s, jalr, illegal_address;
        cp_load_access_fault:                    cross priv_mode_s, loadops, illegal_address;
        cp_store_access_fault:                   cross priv_mode_s, storeops, illegal_address;
        cp_misaligned_priority:                  cross priv_mode_s, sw_lw_jalr, illegal_address_misaligned;
    `endif

endgroup

`endif // S_SUPPORTED

`ifndef EXCLUDE_SM
covergroup Exceptions_Sm_cg with function sample(ins_t ins);
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
    `ifdef ZIBI_SUPPORTED
        zibi_branches_taken: coverpoint {ins.current.insn[6:0], ins.current.insn[14:12],
                                         ins.current.rs1_val == ins.current.imm2} {
            bins beqi_taken = {11'b1100011_010_1};
            bins bnei_taken = {11'b1100011_011_0};
        }
        zibi_branches_nottaken: coverpoint {ins.current.insn[6:0], ins.current.insn[14:12],
                                            ins.current.rs1_val == ins.current.imm2} {
            bins beqi_nottaken = {11'b1100011_010_0};
            bins bnei_nottaken = {11'b1100011_011_1};
        }
    `endif
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
        bins ebreak = {EBREAK};
    }
    `ifdef ZCA_SUPPORTED
        // 32-bit ebreak at 62 mod 64: the fetch straddles a 64-byte boundary. xtval must still
        // be zero or the address of the ebreak, never the address of the second half of the fetch.
        straddle64: coverpoint ins.current.pc_rdata[5:1] {
            bins straddle64 = {5'b11111};
        }
    `endif
    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0]  {
        // auto fills 000 through 111
    }
    rs1_zero: coverpoint ins.current.insn[19:15] {
        bins zero = {5'b00000};
    }
    seed: coverpoint ins.current.insn[31:20] {
        bins seed = {CSR_SEED};
    }
    mstatus_MIE: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
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
        medeleg_walk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "medeleg", "medeleg") {
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
        mstatus_SIE: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0] {
            // auto fills 1 and 0
        }
        medeleg_b8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "medeleg", "medeleg")[8] {
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
    `ifdef ZIBI_SUPPORTED
        cp_instr_adr_misaligned_zibi_branch:          cross priv_mode_m, zibi_branches_taken, pc_bit_1, imm_bit_1;
        cp_instr_adr_misaligned_zibi_branch_nottaken: cross priv_mode_m, zibi_branches_nottaken, pc_bit_1, imm_bit_1;
    `endif
    cp_instr_adr_misaligned_jal:             cross priv_mode_m, jal, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jalr:            cross priv_mode_m, jalr, rs1_1_0, offset;
    cp_illegal_instruction:                  cross priv_mode_m, illegalops;
    cp_illegal_instruction_seed:             cross priv_mode_m, csrops, rs1_zero, seed;
    cp_breakpoint:                           cross priv_mode_m, ebreak;
    `ifdef ZCA_SUPPORTED
        cp_ebreak_straddle64:                cross priv_mode_m, ebreak, straddle64;
    `endif
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
        `ifdef UDB_MXLEN_64 // RV64 physical addresses have 56 bits; an RV32 address zero-extends into 34
            i_phys_address_nonexistent: coverpoint ({8'b0, {ins.current.imm + ins.current.rs1_val}[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            i_phys_address_nonexistent: coverpoint ({32'b0, {ins.current.imm + ins.current.rs1_val}[31:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
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


`endif // EXCLUDE_SM

`ifdef U_SUPPORTED
covergroup Exceptions_U_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    ecall: coverpoint ins.current.insn {
        bins ecall  = {ECALL};
    }
    branch: coverpoint ins.current.insn {
        wildcard bins branch = {32'b???????_?????_?????_???_?????_1100011};
    }
    branches_taken: coverpoint {ins.current.insn[14:12],                                               // funct3
                                ins.current.rs1_val == ins.current.rs2_val,                            // A = B
                                $signed(ins.current.rs1_val) < $signed(ins.current.rs2_val),           // A < B (signed)
                                $unsigned(ins.current.rs1_val) < $unsigned(ins.current.rs2_val)} {     // A < B (unsigned)
        wildcard bins beq_taken  = {6'b000_1_?_?};
        wildcard bins bne_taken  = {6'b001_0_?_?};
        wildcard bins blt_taken  = {6'b100_?_1_?};
        wildcard bins bge_taken  = {6'b101_?_0_?};
        wildcard bins bltu_taken = {6'b110_?_?_1};
        wildcard bins bgeu_taken = {6'b111_?_?_0};
    }
    branches_nottaken: coverpoint {ins.current.insn[14:12],                                              // funct3
                                   ins.current.rs1_val == ins.current.rs2_val,                           // A == B
                                   $signed(ins.current.rs1_val) < $signed(ins.current.rs2_val),          // A < B (signed)
                                   $unsigned(ins.current.rs1_val) < $unsigned(ins.current.rs2_val)} {    // A < B (unsigned)
        wildcard bins beq_nottaken  = {6'b000_0_?_?};
        wildcard bins bne_nottaken  = {6'b001_1_?_?};
        wildcard bins blt_nottaken  = {6'b100_?_0_?};
        wildcard bins bge_nottaken  = {6'b101_?_1_?};
        wildcard bins bltu_nottaken = {6'b110_?_?_0};
        wildcard bins bgeu_nottaken = {6'b111_?_?_1};
    }
    `ifdef ZIBI_SUPPORTED
        zibi_branches_taken: coverpoint {ins.current.insn[6:0], ins.current.insn[14:12],
                                         ins.current.rs1_val == ins.current.imm2} {
            bins beqi_taken = {11'b1100011_010_1};
            bins bnei_taken = {11'b1100011_011_0};
        }
        zibi_branches_nottaken: coverpoint {ins.current.insn[6:0], ins.current.insn[14:12],
                                            ins.current.rs1_val == ins.current.imm2} {
            bins beqi_nottaken = {11'b1100011_010_0};
            bins bnei_nottaken = {11'b1100011_011_1};
        }
    `endif
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
        bins ebreak = {EBREAK};
    }
    `ifdef ZCA_SUPPORTED
        // 32-bit ebreak at 62 mod 64: the fetch straddles a 64-byte boundary. xtval must still
        // be zero or the address of the ebreak, never the address of the second half of the fetch.
        straddle64: coverpoint ins.current.pc_rdata[5:1] {
            bins straddle64 = {5'b11111};
        }
    `endif
    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0]  {
        // auto fills 000 through 111
    }
    rs1_zero: coverpoint ins.current.insn[19:15] {
        bins zero = {5'b00000};
    }
    seed: coverpoint ins.current.insn[31:20] {
        bins seed = {CSR_SEED};
    }
    mstatus_MIE: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0] {
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
    cp_instr_adr_misaligned_branch:          cross priv_mode_u, branch, branches_taken, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_branch_nottaken: cross priv_mode_u, branch, branches_nottaken, pc_bit_1, imm_bit_1;
    `ifdef ZIBI_SUPPORTED
        cp_instr_adr_misaligned_zibi_branch:          cross priv_mode_u, zibi_branches_taken, pc_bit_1, imm_bit_1;
        cp_instr_adr_misaligned_zibi_branch_nottaken: cross priv_mode_u, zibi_branches_nottaken, pc_bit_1, imm_bit_1;
    `endif
    cp_instr_adr_misaligned_jal:             cross priv_mode_u, jal, pc_bit_1, imm_bit_1;
    cp_instr_adr_misaligned_jalr:            cross priv_mode_u, jalr, rs1_1_0, offset;
    cp_illegal_instruction:                  cross priv_mode_u, illegalops;
    cp_illegal_instruction_seed:             cross priv_mode_u, csrops, rs1_zero, seed;
    cp_breakpoint:                           cross priv_mode_u, ebreak;
    `ifdef ZCA_SUPPORTED
        cp_ebreak_straddle64:                cross priv_mode_u, ebreak, straddle64;
    `endif
    cp_load_address_misaligned:              cross priv_mode_u, loadops, adr_LSBs;
    cp_store_address_misaligned:             cross priv_mode_u, storeops, adr_LSBs;
    cp_ecall_u:                              cross priv_mode_u, ecall;
    cp_mstatus_ie:                           cross priv_mode_u, ecall, mstatus_MIE;

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        illegal_address_priority: coverpoint {{ins.current.imm + ins.current.rs1_val}[`UDB_MXLEN-1:3], 3'b000} {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        cp_instr_access_fault:                   cross priv_mode_u, jalr, illegal_address;
        cp_load_access_fault:                    cross priv_mode_u, loadops, illegal_address;
        cp_misaligned_priority_load:             cross priv_mode_u, loadops, adr_LSBs, illegal_address_priority;
        cp_misaligned_priority_store:            cross priv_mode_u, storeops, adr_LSBs, illegal_address_priority;
        cp_store_access_fault:                   cross priv_mode_u, storeops, illegal_address;
    `endif


endgroup

`endif // U_SUPPORTED

`ifdef ZAAMO_SUPPORTED
covergroup Exceptions_Zaamo_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // building blocks for the main coverpoints
    amo_instrs: coverpoint ins.current.insn {
        wildcard bins amoswap_w = {AMOSWAP_W};
        wildcard bins amoadd_w  = {AMOADD_W};
        wildcard bins amoand_w  = {AMOAND_W};
        wildcard bins amoor_w   = {AMOOR_W};
        wildcard bins amoxor_w  = {AMOXOR_W};
        wildcard bins amomax_w  = {AMOMAX_W};
        wildcard bins amomaxu_w = {AMOMAXU_W};
        wildcard bins amomin_w  = {AMOMIN_W};
        wildcard bins amominu_w = {AMOMINU_W};
        `ifdef ZACAS_SUPPORTED
          wildcard bins amocas_w  = {AMOCAS_W};
          wildcard bins amocas_d  = {AMOCAS_D};
        `endif
        `ifdef UDB_MXLEN_64
            wildcard bins amoswap_d = {AMOSWAP_D};
            wildcard bins amoadd_d  = {AMOADD_D};
            wildcard bins amoand_d  = {AMOAND_D};
            wildcard bins amoor_d   = {AMOOR_D};
            wildcard bins amoxor_d  = {AMOXOR_D};
            wildcard bins amomax_d  = {AMOMAX_D};
            wildcard bins amomaxu_d = {AMOMAXU_D};
            wildcard bins amomin_d  = {AMOMIN_D};
            wildcard bins amominu_d = {AMOMINU_D};
            `ifdef ZACAS_SUPPORTED
              wildcard bins amocas_q  = {AMOCAS_Q};
            `endif
        `endif
        `ifdef ZABHA_SUPPORTED
            wildcard bins amoswap_h = {AMOSWAP_H};
            wildcard bins amoadd_h  = {AMOADD_H};
            wildcard bins amoand_h  = {AMOAND_H};
            wildcard bins amoor_h   = {AMOOR_H};
            wildcard bins amoxor_h  = {AMOXOR_H};
            wildcard bins amomax_h  = {AMOMAX_H};
            wildcard bins amomaxu_h = {AMOMAXU_H};
            wildcard bins amomin_h  = {AMOMIN_H};
            wildcard bins amominu_h = {AMOMINU_H};
            wildcard bins amoswap_b = {AMOSWAP_B};
            wildcard bins amoadd_b  = {AMOADD_B};
            wildcard bins amoand_b  = {AMOAND_B};
            wildcard bins amoor_b   = {AMOOR_B};
            wildcard bins amoxor_b  = {AMOXOR_B};
            wildcard bins amomax_b  = {AMOMAX_B};
            wildcard bins amomaxu_b = {AMOMAXU_B};
            wildcard bins amomin_b  = {AMOMIN_B};
            wildcard bins amominu_b = {AMOMINU_B};
        `endif
    }
    // TODO: adjust number of lsbs based on MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE
    adr_LSBs: coverpoint ins.current.rs1_val[4:0]  {
        // auto fills 00000 through 11111
    }
    // main coverpoints
    cp_amo_address_misaligned:  cross amo_instrs, adr_LSBs;

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        cp_amo_access_fault:        cross amo_instrs, illegal_address;
    `endif

endgroup

`endif // ZAAMO_SUPPORTED

`ifdef ZALRSC_SUPPORTED
covergroup Exceptions_Zalrsc_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // building blocks for the main coverpoints
    lr: coverpoint ins.current.insn {
        wildcard bins lr_w = {LR_W};
        `ifdef UDB_MXLEN_64
            wildcard bins lr_d = {LR_D};
        `endif
    }
    sc: coverpoint ins.current.insn {
        wildcard bins sc_w = {SC_W};
        `ifdef UDB_MXLEN_64
            wildcard bins sc_d = {SC_D};
        `endif
    }
    lr_w: coverpoint ins.current.insn {
    wildcard bins lr_w = {LR_W};
    }
    sc_w: coverpoint ins.current.insn {
        wildcard bins sc_w = {SC_W};
    }
    `ifdef UDB_MXLEN_64
        lr_d: coverpoint ins.current.insn {
            wildcard bins lr_d = {LR_D};
        }
        sc_d: coverpoint ins.current.insn {
                wildcard bins sc_d = {SC_D};
        }
        adr_LSBs_illegal_d: coverpoint ins.current.rs1_val[2:0]  {
        ignore_bins zero = {0};
        }
        adr_LSBs_legal_d: coverpoint ins.current.rs1_val[2:0]  {
            bins zero = {0};
        }
    `endif

    adr_LSBs_illegal_w: coverpoint ins.current.rs1_val[2:0]  {
        ignore_bins zero = {0};
        ignore_bins four = {3'b100};
    }
    adr_LSBs_legal_w: coverpoint ins.current.rs1_val[2:0]  {
        bins zero = {0};
        bins four = {3'b100};
    }
    rd_gt_one_prev: coverpoint ins.prev.rd_val {
        bins nonzero = {[2:$]};
    }
    rd_gt_one_cur: coverpoint ins.current.rd_val {
        bins nonzero = {[2:$]};
    }
    rd_zero_cur: coverpoint ins.current.rd_val {
        bins zero = {0};
    }
    adr_LSBs: coverpoint ins.current.rs1_val[2:0]  {
        // auto fills 000 through 111
    }

    // Ideally this coverpoint would check the rs1 of the paired lr.x and sc.x
    // to match the test plan. With our current toolflow
    // Testing that the rs1 value of the previous lr.x matches the rs1 of the sc.x
    // is not possible.
    // As a proxy we can check that the rd value changes as expected for rd when an
    // sc.x instruction is executed. Load rd with a value > 1.
    // Faulting instructions should not modify the rd value while
    // Successful instructions should write 0 to rd.
    // sc.w and sc.d have a different set of legal LSB offset
    // (4 byte aligned vs ) so they are handled differently in the coverpoints.

    // main coverpoints


    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        illegal_address_misaligned: coverpoint ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS + 1};
        }
        non_illegal_address: coverpoint (64'({{ins.current.imm + ins.current.rs1_val}[`UDB_MXLEN-1:3], 3'b000}) != `RVMODEL_ACCESS_FAULT_ADDRESS) {
            bins non_illegal = {1};
        }
        cp_load_address_misaligned:                cross lr, adr_LSBs, non_illegal_address;
        cp_load_access_fault:                      cross lr, illegal_address;
        cp_load_access_misaligned_priority:        cross lr, illegal_address_misaligned;
        cp_store_address_misaligned_legal_w:       cross sc_w, adr_LSBs_legal_w,rd_gt_one_prev, rd_zero_cur, non_illegal_address;
        cp_store_address_misaligned_illegal_w:     cross sc_w, adr_LSBs_illegal_w, rd_gt_one_prev, rd_gt_one_cur, non_illegal_address;
        `ifdef UDB_MXLEN_64
            cp_store_address_misaligned_legal_d:     cross sc_d, adr_LSBs_legal_d,rd_gt_one_prev, rd_zero_cur, non_illegal_address;
            cp_store_address_misaligned_illegal_d:   cross sc_d, adr_LSBs_illegal_d, rd_gt_one_prev, rd_gt_one_cur, non_illegal_address;
        `endif
        cp_store_access_fault:                cross sc, illegal_address, rd_gt_one_prev, rd_gt_one_cur;
        cp_store_access_misaligned_priority:  cross sc, illegal_address_misaligned, rd_gt_one_prev, rd_gt_one_cur;
    `else // if no access faults, exclude non_illegal_address condition
        cp_load_address_misaligned:                cross lr, adr_LSBs;
        cp_store_address_misaligned_legal_w:       cross sc_w, adr_LSBs_legal_w,rd_gt_one_prev, rd_zero_cur;
        cp_store_address_misaligned_illegal_w:     cross sc_w, adr_LSBs_illegal_w, rd_gt_one_prev, rd_gt_one_cur;
        `ifdef UDB_MXLEN_64
            cp_store_address_misaligned_legal_d:     cross sc_d, adr_LSBs_legal_d,rd_gt_one_prev, rd_zero_cur;
            cp_store_address_misaligned_illegal_d:   cross sc_d, adr_LSBs_illegal_d, rd_gt_one_prev, rd_gt_one_cur;
        `endif
    `endif
endgroup

`endif // ZALRSC_SUPPORTED

`ifdef ZCA_SUPPORTED
covergroup Exceptions_Zc_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // building blocks for the main coverpoints
    loadops: coverpoint ins.current.insn {

        wildcard bins c_lw    = {C_LW};
        wildcard bins c_lwsp  = {C_LWSP};
        `ifdef ZCB_SUPPORTED
            wildcard bins c_lh    = {C_LH};
            wildcard bins c_lhu   = {C_LHU};
            wildcard bins c_lbu   = {C_LBU};
        `endif
        `ifdef ZCD_SUPPORTED
            wildcard bins c_fld   = {C_FLD};
            wildcard bins c_fldsp = {C_FLDSP};
        `endif
        `ifdef ZCF_SUPPORTED // UDB_MXLEN_32
            wildcard bins c_flw   = {C_FLW};
            wildcard bins c_flwsp = {C_FLWSP};
        `endif

        `ifdef UDB_MXLEN_64
            wildcard bins c_ld   = {C_LD};
            wildcard bins c_ldsp = {C_LDSP};
        `endif

    }

    storeops: coverpoint ins.current.insn {
        wildcard bins c_sw    = {C_SW};
        wildcard bins c_swsp  = {C_SWSP};
        `ifdef ZCB_SUPPORTED
            wildcard bins c_sb    = {C_SB};
            wildcard bins c_sh    = {C_SH};
        `endif
        `ifdef ZCD_SUPPORTED
            wildcard bins c_fsd   = {C_FSD};
            wildcard bins c_fsdsp = {C_FSDSP};
        `endif
        `ifdef ZCF_SUPPORTED // only supported in UDB_MXLEN_32
            wildcard bins c_fsw   = {C_FSW};
            wildcard bins c_fswsp = {C_FSWSP};
        `endif

        `ifdef UDB_MXLEN_64
            wildcard bins c_sd   = {C_SD};
            wildcard bins c_sdsp = {C_SDSP};
        `endif

    }

    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0]  {
        // auto fills 000 through 111
    }

    // main coverpoints
    cp_breakpoint:                           coverpoint ins.current.insn[15:0] {bins c_ebreak = {16'h9002};}
    cp_load_address_misaligned:              cross loadops, adr_LSBs;
    cp_store_address_misaligned:             cross storeops, adr_LSBs;
    cp_illegal_instruction:                  coverpoint ins.current.insn[15:0] { bins illegal0 = {'0}; }

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        cp_load_access_fault:                    cross loadops, illegal_address;
        cp_store_access_fault:                   cross storeops, illegal_address;
    `endif
endgroup

`endif // ZCA_SUPPORTED

`ifdef S_SUPPORTED
`ifdef EXCEPTIONS_ZICBO_ANY
covergroup Exceptions_ZicboS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    `ifdef ZICBOM_SUPPORTED
        cbo_inval: coverpoint ins.current.insn {
            wildcard bins cbo_inval = {CBO_INVAL};
        }
        cbo_flushclean: coverpoint ins.current.insn {
            wildcard bins cbo_flush = {CBO_FLUSH};
            wildcard bins cbo_clean = {CBO_CLEAN};
        }
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            menvcfg_cbie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbie")[1:0] {
                ignore_bins reserved = {2'b10};
            }
            menvcfg_cbcfe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbcfe")[0] {
            }
        `endif
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            senvcfg_cbie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "cbie")[1:0] {
                ignore_bins reserved = {2'b10};
            }
            senvcfg_cbcfe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "cbcfe")[0] {
            }
        `endif
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cbo_zero: coverpoint ins.current.insn {
            wildcard bins cbo_zero = {CBO_ZERO};
        }
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            menvcfg_cbze: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbze")[0] {
            }
        `endif
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            senvcfg_cbze: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "cbze")[0] {
            }
        `endif
    `endif

    adr_misaligned: coverpoint ins.current.rs1_val[0]  {
    }
    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        menvcfg_all_enable: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "menvcfg")[7:4] {
            bins ones = {4'b1111};
        }
    `endif
    `ifdef S1P12P0_OR_LATER_SUPPORTED
        senvcfg_all_enable: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "senvcfg")[7:4] {
            bins ones = {4'b1111};
        }
    `endif
    cbo_instrs: coverpoint ins.current.insn {
        `ifdef ZICBOM_SUPPORTED
            wildcard bins inval  = {CBO_INVAL};
            wildcard bins clean  = {CBO_CLEAN};
            wildcard bins flush  = {CBO_FLUSH};
        `endif
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins zero   = {CBO_ZERO};
        `endif
        wildcard bins prefetch_i  = {PREFETCH_I};
        wildcard bins prefetch_w  = {PREFETCH_W};
        wildcard bins prefetch_r  = {PREFETCH_R};
    }

    // cbie/cbcfe/cbze crosses need both menvcfg (Sm1.12+) and senvcfg (S1.12+)
    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        `ifdef S1P12P0_OR_LATER_SUPPORTED
            `ifdef ZICBOM_SUPPORTED
                cp_cbie:  cross cbo_inval,      menvcfg_cbie,  senvcfg_cbie,  priv_mode_s_u;
                cp_cbcfe: cross cbo_flushclean, menvcfg_cbcfe, senvcfg_cbcfe, priv_mode_s_u;
            `endif
            `ifdef ZICBOZ_SUPPORTED
                cp_cbze:  cross cbo_zero,       menvcfg_cbze,  senvcfg_cbze,  priv_mode_s_u;
            `endif
            cp_cbo_address_misaligned:  cross cbo_instrs, adr_misaligned, priv_mode_s_u, menvcfg_all_enable, senvcfg_all_enable;
        `else
            cp_cbo_address_misaligned:  cross cbo_instrs, adr_misaligned, priv_mode_s_u;
        `endif
    `else
        cp_cbo_address_misaligned:  cross cbo_instrs, adr_misaligned, priv_mode_s_u;
    `endif

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint {ins.current.rs1_val[XLEN-1:1], 1'b0} {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            `ifdef S1P12P0_OR_LATER_SUPPORTED
                cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_s_u, menvcfg_all_enable, senvcfg_all_enable;
            `else
                cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_s_u;
            `endif
        `else
            cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_s_u;
        `endif
    `endif

endgroup

`endif // EXCEPTIONS_ZICBO_ANY
`endif // S_SUPPORTED

`ifndef EXCLUDE_SM
`ifdef EXCEPTIONS_ZICBO_ANY
covergroup Exceptions_ZicboSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    `ifdef ZICBOM_SUPPORTED
        cbo_inval: coverpoint ins.current.insn {
            wildcard bins cbo_inval = {CBO_INVAL};
        }
        cbo_flushclean: coverpoint ins.current.insn {
            wildcard bins cbo_flush = {CBO_FLUSH};
            wildcard bins cbo_clean = {CBO_CLEAN};
        }

        // menvcfg does not exist before Sm1.12.0
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            `ifdef U_SUPPORTED
                menvcfg_cbie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbie")[1:0] {
                    ignore_bins reserved = {2'b10};
                }
                menvcfg_cbcfe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbcfe")[0] {
                }
            `endif
        `endif
    `endif

    `ifdef ZICBOZ_SUPPORTED
        cbo_zero: coverpoint ins.current.insn {
            wildcard bins cbo_zero = {CBO_ZERO};
        }

        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            `ifdef U_SUPPORTED
                menvcfg_cbze: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbze")[0] {
                }
            `endif
        `endif
    `endif

    adr_misaligned: coverpoint ins.current.rs1_val[0]  {
    }

    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        `ifdef U_SUPPORTED
            menvcfg_all_enable: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "menvcfg")[7:4] {
                bins ones = {4'b1111};
            }
        `endif
    `endif
    cbo_instrs: coverpoint ins.current.insn {
        `ifdef ZICBOM_SUPPORTED
            wildcard bins inval  = {CBO_INVAL};
            wildcard bins clean  = {CBO_CLEAN};
            wildcard bins flush  = {CBO_FLUSH};
        `endif
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins zero   = {CBO_ZERO};
        `endif
        wildcard bins prefetch_i = {PREFETCH_I};
        wildcard bins prefetch_w = {PREFETCH_W};
        wildcard bins prefetch_r = {PREFETCH_R};
    }

    // main coverpoints
    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        `ifdef U_SUPPORTED
            `ifdef ZICBOM_SUPPORTED
                cp_cbie: cross cbo_inval, menvcfg_cbie, priv_mode_m;
                cp_cbcfe: cross cbo_flushclean, menvcfg_cbcfe, priv_mode_m;
            `endif
            `ifdef ZICBOZ_SUPPORTED
                cp_cbze: cross cbo_zero, menvcfg_cbze, priv_mode_m;
            `endif
            cp_cbo_address_misaligned: cross cbo_instrs, adr_misaligned, priv_mode_m, menvcfg_all_enable;
        `else
            cp_cbo_address_misaligned: cross cbo_instrs, adr_misaligned, priv_mode_m;
        `endif
    `else
        cp_cbo_address_misaligned:  cross cbo_instrs, adr_misaligned, priv_mode_m;
    `endif

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint {ins.current.rs1_val[XLEN-1:1], 1'b0} {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }

        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            `ifdef U_SUPPORTED
                cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_m, menvcfg_all_enable;
            `else
                cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_m;
            `endif
        `else
            cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_m;
        `endif
    `endif
endgroup

`endif // EXCEPTIONS_ZICBO_ANY
`endif // EXCLUDE_SM

`ifdef U_SUPPORTED
`ifdef EXCEPTIONS_ZICBO_ANY
covergroup Exceptions_ZicboU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    `ifdef ZICBOM_SUPPORTED
        cbo_inval: coverpoint ins.current.insn {
            wildcard bins cbo_inval = {CBO_INVAL};
        }
        cbo_flushclean: coverpoint ins.current.insn {
            wildcard bins cbo_flush = {CBO_FLUSH};
            wildcard bins cbo_clean = {CBO_CLEAN};
        }
        // menvcfg does not exist before Sm1.12.0
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            menvcfg_cbie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbie")[1:0] {
                ignore_bins reserved = {2'b10};
            }
            menvcfg_cbcfe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbcfe")[0] {
            }
        `endif
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cbo_zero: coverpoint ins.current.insn {
            wildcard bins cbo_zero = {CBO_ZERO};
        }
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            menvcfg_cbze: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "cbze")[0] {
            }
        `endif
    `endif

    adr_misaligned: coverpoint ins.current.rs1_val[0]  {
    }
    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        menvcfg_all_enable: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "menvcfg")[7:4] {
            bins ones = {4'b1111};
        }
    `endif
    cbo_instrs: coverpoint ins.current.insn {
        `ifdef ZICBOM_SUPPORTED
            wildcard bins inval = {CBO_INVAL};
            wildcard bins clean  = {CBO_CLEAN};
            wildcard bins flush  = {CBO_FLUSH};
        `endif
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins zero   = {CBO_ZERO};
        `endif
        wildcard bins prefetch_i  = {PREFETCH_I};
        wildcard bins prefetch_w  = {PREFETCH_W};
        wildcard bins prefetch_r  = {PREFETCH_R};
    }

    // main coverpoints
    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        `ifdef ZICBOM_SUPPORTED
            cp_cbie:  cross cbo_inval,      menvcfg_cbie,  priv_mode_u;
            cp_cbcfe: cross cbo_flushclean, menvcfg_cbcfe, priv_mode_u;
        `endif
        `ifdef ZICBOZ_SUPPORTED
            cp_cbze:  cross cbo_zero,       menvcfg_cbze,  priv_mode_u;
        `endif
        cp_cbo_address_misaligned:  cross cbo_instrs, adr_misaligned, priv_mode_u, menvcfg_all_enable;
    `else
        cp_cbo_address_misaligned:  cross cbo_instrs, adr_misaligned, priv_mode_u;
    `endif

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint {ins.current.rs1_val[XLEN-1:1], 1'b0} {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_u, menvcfg_all_enable;
        `else
            cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_u;
        `endif
    `endif

endgroup

`endif // EXCEPTIONS_ZICBO_ANY
`endif // U_SUPPORTED

function void exceptions_sample(int hart, int issue, ins_t ins);
`ifdef F_SUPPORTED
    Exceptions_F_cg.sample(ins);
`endif // F_SUPPORTED
`ifdef S_SUPPORTED
    Exceptions_S_cg.sample(ins);
`endif // S_SUPPORTED
`ifndef EXCLUDE_SM
    Exceptions_Sm_cg.sample(ins);
`endif // EXCLUDE_SM
`ifdef U_SUPPORTED
    Exceptions_U_cg.sample(ins);
`endif // U_SUPPORTED
`ifdef ZAAMO_SUPPORTED
    Exceptions_Zaamo_cg.sample(ins);
`endif // ZAAMO_SUPPORTED
`ifdef ZALRSC_SUPPORTED
    Exceptions_Zalrsc_cg.sample(ins);
`endif // ZALRSC_SUPPORTED
`ifdef ZCA_SUPPORTED
    Exceptions_Zc_cg.sample(ins);
`endif // ZCA_SUPPORTED
`ifdef EXCEPTIONS_ZICBO_ANY
  `ifdef S_SUPPORTED
      Exceptions_ZicboS_cg.sample(ins);
  `endif // S_SUPPORTED
  `ifndef EXCLUDE_SM
      Exceptions_ZicboSm_cg.sample(ins);
  `endif // EXCLUDE_SM
  `ifdef U_SUPPORTED
      Exceptions_ZicboU_cg.sample(ins);
  `endif // U_SUPPORTED
`endif // EXCEPTIONS_ZICBO_ANY
endfunction
