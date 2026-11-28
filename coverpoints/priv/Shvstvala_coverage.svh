///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Shvstvala: traps from VS-mode and VU-mode into VS-mode write vstval as Sstvala requires for stval.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SHVSTVALA

`include "general/RISCV_coverage_hypervisor.svh"

covergroup Shvstvala_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // The instruction coverpoints and vstval_address and vstval_target serve crosses that a config may compile
    // out, so only the crosses count
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
    lw : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lw = {LW};
    }
    sw : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins sw = {SW};
    }
    jalr : coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins jalr = {JALR};
    }
    illegal : coverpoint ins.current.insn {
        bins zeros = {'0};
        bins ones  = {'1};
    }

    // vstval holds the load or store address, the jalr target, or the instruction.  The test sets vstval
    // to a random value before each trap.
    vstval_address : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSTVAL) ==
                                ins.current.eff_addr {
        type_option.weight = 0;
        bins match = {1};
    }
    vstval_target : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSTVAL) ==
                               (ins.current.eff_addr & ~1) {
        type_option.weight = 0;
        bins match = {1};
    }

    // An exception whose medeleg bit is read-only 0 (MEDELEG_DELEGATABLE false) is taken in M-mode and never
    // reaches VS-mode, so each exception's coverpoints need that bit
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_FETCH
        `ifdef UDB_MEDELEG_DELEGATABLE_1
            instr_access_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {1};
            }
            cp_instr_access_fault: cross priv_mode_vs_vu, jalr,     instr_access_fault, vstval_target;
        `endif
    `endif
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
        `ifdef UDB_MEDELEG_DELEGATABLE_5
            load_access_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {5};
            }
            cp_load_access_fault:  cross priv_mode_vs_vu, loadops,  load_access_fault,  vstval_address;
        `endif
    `endif
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_STORE
        `ifdef UDB_MEDELEG_DELEGATABLE_7
            store_access_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {7};
            }
            cp_store_access_fault: cross priv_mode_vs_vu, storeops, store_access_fault, vstval_address;
        `endif
    `endif

    // Misaligned loads and stores trap only when the implementation does not perform them
    `ifndef UDB_MISALIGNED_LDST
        // Each misalignment of words, and of doublewords on RV64: the address offset within the access's natural
        // alignment.  A halfword can only be misaligned by 1, which cp_load/store_address_misaligned cover.
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
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_4
            load_misaligned : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {4};
            }
            cp_load_address_misaligned:  cross priv_mode_vs_vu, wide_loadops,  load_misaligned,  vstval_address;
            cp_load_misaligned_word:  cross priv_mode_vs_vu, word_loadops,  load_misaligned,  word_misalignment, vstval_address;
            `ifdef UDB_MXLEN_64
                cp_load_misaligned_doubleword:  cross priv_mode_vs_vu, ld, load_misaligned,  doubleword_misalignment, vstval_address;
            `endif
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_6
            store_misaligned : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {6};
            }
            cp_store_address_misaligned: cross priv_mode_vs_vu, wide_storeops, store_misaligned, vstval_address;
            cp_store_misaligned_word: cross priv_mode_vs_vu, word_storeops, store_misaligned, word_misalignment, vstval_address;
            `ifdef UDB_MXLEN_64
                cp_store_misaligned_doubleword: cross priv_mode_vs_vu, sd, store_misaligned, doubleword_misalignment, vstval_address;
            `endif
        `endif
    `endif

    // Misaligned fetches trap only when IALIGN = 32
    `ifndef ZCA_SUPPORTED
        `ifdef UDB_MEDELEG_DELEGATABLE_0
            instr_misaligned : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {0};
            }
            cp_instr_adr_misaligned_jalr: cross priv_mode_vs_vu, jalr, instr_misaligned, vstval_target;
        `endif
    `endif

    `ifdef UDB_MEDELEG_DELEGATABLE_2
        vstval_insn : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSTVAL) == `UDB_MXLEN'(ins.current.insn) {
            bins match = {1};
        }
        illegal_instruction : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
            bins vscause = {2};
        }
        cp_illegal_instruction: cross priv_mode_vs_vu, illegal, illegal_instruction, vstval_insn;
    `endif

    // VS-stage leaves without R, W or X under two-stage translation
    `ifdef H_TWO_STAGE
        `ifdef UDB_MEDELEG_DELEGATABLE_12
            instr_page_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {12};
            }
            cp_instr_page_fault: cross priv_mode_vs_vu, jalr, instr_page_fault, vstval_target;
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_13
            load_page_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {13};
            }
            cp_load_page_fault:  cross priv_mode_vs_vu, lw,   load_page_fault,  vstval_address;
        `endif
        `ifdef UDB_MEDELEG_DELEGATABLE_15
            store_page_fault : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_VSCAUSE, "code")
                iff (ins.current.csr_wb[CSR_VSCAUSE]) {
                bins vscause = {15};
            }
            cp_store_page_fault: cross priv_mode_vs_vu, sw,   store_page_fault, vstval_address;
        `endif
    `endif
endgroup

function void shvstvala_sample(int hart, int issue, ins_t ins);
    Shvstvala_cg.sample(ins);
endfunction
