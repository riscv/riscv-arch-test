///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// Sstvala Coverage
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//


`define COVER_SSTVALA

covergroup Sstvala_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // The instruction coverpoints and stval_address and stval_target serve crosses that a config may compile out,
    // so only the crosses count
    loadops : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lb  = {LB};
        wildcard bins lbu = {LBU};
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lw  = {LW};
        `ifdef UDB_MXLEN_64
            wildcard bins lwu = {LWU};
            wildcard bins ld  = {LD};
        `endif
    }
    storeops : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
        `endif
    }
    // Loads and stores wider than a byte, which can be misaligned
    wide_loadops : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lw  = {LW};
        `ifdef UDB_MXLEN_64
            wildcard bins lwu = {LWU};
            wildcard bins ld  = {LD};
        `endif
    }
    wide_storeops : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
        `endif
    }
    // The page-fault tests load and store words, and doublewords on RV64
    pf_loadops : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lw = {LW};
        `ifdef UDB_MXLEN_64
            wildcard bins ld = {LD};
        `endif
    }
    pf_storeops : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
        `endif
    }
    jalr : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins jalr = {JALR};
    }
    illegal : coverpoint ins.current.insn {
        bins zeros = {'0};
        bins ones  = {'1};
    }

    // stval holds the load or store address, the jalr target, or the instruction.  The test sets stval to a
    // random value before each trap.
    stval_address : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_STVAL) ==
                               ins.current.eff_addr {
        type_option.weight = 0;
        bins match = {1};
    }
    stval_target : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_STVAL) ==
                              (ins.current.eff_addr & ~1) {
        type_option.weight = 0;
        bins match = {1};
    }

    // An exception whose medeleg bit is read-only 0 (MEDELEG_DELEGATABLE false) is taken in M-mode, which does not write stval, so each
    // exception's coverpoints need that bit
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_FETCH
        `ifdef UDB_MEDELEG_DELEGATABLE_1
            instr_access_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {1};
            }
            cp_instr_access_fault: cross priv_mode_s_u, jalr,     instr_access_fault, stval_target;
        `endif
    `endif
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
        `ifdef UDB_MEDELEG_DELEGATABLE_5
            load_access_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {5};
            }
            cp_load_access_fault:  cross priv_mode_s_u, loadops,  load_access_fault,  stval_address;
        `endif
    `endif
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_STORE
        `ifdef UDB_MEDELEG_DELEGATABLE_7
            store_access_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {7};
            }
            cp_store_access_fault: cross priv_mode_s_u, storeops, store_access_fault, stval_address;
        `endif
    `endif

    // Misaligned loads and stores trap only when the implementation does not perform them
    `ifndef UDB_MISALIGNED_LDST
        `ifdef UDB_MEDELEG_DELEGATABLE_4
            load_misaligned : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {4};
            }
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_6
            store_misaligned : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {6};
            }
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_4
            cp_load_address_misaligned:  cross priv_mode_s_u, wide_loadops,  load_misaligned,  stval_address;
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_6
            cp_store_address_misaligned: cross priv_mode_s_u, wide_storeops, store_misaligned, stval_address;
        `endif
        // Each misalignment of words, and of doublewords on RV64: the address offset within the access's natural
        // alignment.  A halfword can only be misaligned by 1, which the crosses above cover.
        word_loadops : coverpoint ins.current.insn {
            type_option.weight = 0;
            wildcard bins lw  = {LW};
            `ifdef UDB_MXLEN_64
                wildcard bins lwu = {LWU};
            `endif
        }
        word_storeops : coverpoint ins.current.insn {
            type_option.weight = 0;
            wildcard bins sw = {SW};
        }
        word_misalignment : coverpoint ins.current.eff_addr & 3 {
            type_option.weight = 0;
            bins offset[] = {[1:3]};
        }
        `ifdef UDB_MEDELEG_DELEGATABLE_4
            cp_load_misaligned_word:  cross priv_mode_s_u, word_loadops,  load_misaligned,  word_misalignment, stval_address;
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_6
            cp_store_misaligned_word: cross priv_mode_s_u, word_storeops, store_misaligned, word_misalignment, stval_address;
        `endif
        `ifdef UDB_MXLEN_64
            ld : coverpoint ins.current.insn {
                type_option.weight = 0;
                wildcard bins ld = {LD};
            }
            sd : coverpoint ins.current.insn {
                type_option.weight = 0;
                wildcard bins sd = {SD};
            }
            doubleword_misalignment : coverpoint ins.current.eff_addr & 7 {
                type_option.weight = 0;
                bins offset[] = {[1:7]};
            }
            `ifdef UDB_MEDELEG_DELEGATABLE_4
                cp_load_misaligned_doubleword:  cross priv_mode_s_u, ld, load_misaligned,  doubleword_misalignment, stval_address;
            `endif
            `ifdef UDB_MEDELEG_DELEGATABLE_6
                cp_store_misaligned_doubleword: cross priv_mode_s_u, sd, store_misaligned, doubleword_misalignment, stval_address;
            `endif
        `endif
    `endif

    // Misaligned fetches trap only when IALIGN = 32
    `ifndef ZCA_SUPPORTED
        `ifdef UDB_MEDELEG_DELEGATABLE_0
            instr_misaligned : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {0};
            }
            cp_instr_adr_misaligned_jalr: cross priv_mode_s_u, jalr, instr_misaligned, stval_target;
        `endif
    `endif

    `ifdef UDB_MEDELEG_DELEGATABLE_2
        stval_insn : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_STVAL) == `UDB_MXLEN'(ins.current.insn) {
            bins match = {1};
        }
        illegal_instruction : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
            bins scause = {2};
        }
        cp_illegal_instruction: cross priv_mode_s_u, illegal, illegal_instruction, stval_insn;
    `endif

    // Leaves without R, W or X under Sv39 (RV64) or Sv32 (RV32), in S-mode
    `ifdef UDB_MXLEN_64
        `ifdef SV39_SUPPORTED
            `define SSTVALA_PAGE_FAULTS
        `endif
    `elsif SV32_SUPPORTED
        `define SSTVALA_PAGE_FAULTS
    `endif
    `ifdef SSTVALA_PAGE_FAULTS
        `ifdef UDB_MEDELEG_DELEGATABLE_12
            instr_page_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {12};
            }
            cp_instr_page_fault: cross priv_mode_s, jalr,        instr_page_fault, stval_target;
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_13
            load_page_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {13};
            }
            cp_load_page_fault:  cross priv_mode_s, pf_loadops,  load_page_fault,  stval_address;
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_15
            store_page_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code")
                iff (ins.current.csr_wb[CSR_SCAUSE]) {
                bins scause = {15};
            }
            cp_store_page_fault: cross priv_mode_s, pf_storeops, store_page_fault, stval_address;
        `endif
    `endif
endgroup

`ifdef SSTVALA_PAGE_FAULTS
    `undef SSTVALA_PAGE_FAULTS
`endif

function void sstvala_sample(int hart, int issue, ins_t ins);
    Sstvala_cg.sample(ins);
endfunction
