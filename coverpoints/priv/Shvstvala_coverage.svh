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
    vstval_address : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vstval", "vstval") ==
                                ins.current.rs1_val + ins.current.imm {
        type_option.weight = 0;
        bins match = {1};
    }
    vstval_target : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vstval", "vstval") ==
                               ((ins.current.rs1_val + ins.current.imm) & ~1) {
        type_option.weight = 0;
        bins match = {1};
    }
    vstval_insn : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vstval", "vstval") == ins.current.insn {
        bins match = {1};
    }

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        instr_access_fault : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {1};
        }
        load_access_fault : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {5};
        }
        store_access_fault : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {7};
        }
        cp_load_access_fault:  cross priv_mode_vs_vu, loadops,  load_access_fault,  vstval_address;
        cp_store_access_fault: cross priv_mode_vs_vu, storeops, store_access_fault, vstval_address;
        cp_instr_access_fault: cross priv_mode_vs_vu, jalr,     instr_access_fault, vstval_target;
    `endif

    // Misaligned loads and stores trap only when the implementation does not perform them
    `ifndef UDB_MISALIGNED_LDST
        load_misaligned : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {4};
        }
        store_misaligned : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {6};
        }
        cp_load_address_misaligned:  cross priv_mode_vs_vu, wide_loadops,  load_misaligned,  vstval_address;
        cp_store_address_misaligned: cross priv_mode_vs_vu, wide_storeops, store_misaligned, vstval_address;
    `endif

    // Misaligned fetches trap only when IALIGN = 32
    `ifndef ZCA_SUPPORTED
        instr_misaligned : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {0};
        }
        cp_instr_adr_misaligned_jalr: cross priv_mode_vs_vu, jalr, instr_misaligned, vstval_target;
    `endif

    illegal_instruction : coverpoint ins.current.csr[CSR_VSCAUSE] {
        bins vscause = {2};
    }
    cp_illegal_instruction: cross priv_mode_vs_vu, illegal, illegal_instruction, vstval_insn;

    // VS-stage leaves without R, W or X under two-stage translation
    `ifdef H_TWO_STAGE
        instr_page_fault : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {12};
        }
        load_page_fault : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {13};
        }
        store_page_fault : coverpoint ins.current.csr[CSR_VSCAUSE] {
            bins vscause = {15};
        }
        cp_load_page_fault:  cross priv_mode_vs_vu, lw,   load_page_fault,  vstval_address;
        cp_store_page_fault: cross priv_mode_vs_vu, sw,   store_page_fault, vstval_address;
        cp_instr_page_fault: cross priv_mode_vs_vu, jalr, instr_page_fault, vstval_target;
    `endif
endgroup

function void shvstvala_sample(int hart, int issue, ins_t ins);
    Shvstvala_cg.sample(ins);
endfunction
