///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 25 March 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSSVSM
covergroup ExceptionsSvSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    mstatus_mprv_one: coverpoint ins.current.csr[CSR_MSTATUS][17] {
        bins one = {1};
    }
    mstatus_mpp: coverpoint ins.prev.csr[CSR_MSTATUS][12:11] {
        bins u_mode = {2'b00};
        bins s_mode = {2'b01};
    }
    instr_page_fault: coverpoint (ins.current.csr[CSR_MCAUSE][31:0] == 32'd12) {
        // auto fill 0/1
    }
    load_page_fault: coverpoint (ins.current.csr[CSR_MCAUSE][31:0] == 32'd13) {
        // auto fill 0/1
    }
    store_page_fault: coverpoint (ins.current.csr[CSR_MCAUSE][31:0] == 32'd15) {
        // auto fill 0/1
    }
    i_phys_adr_misaligned: coverpoint ins.current.phys_adr_i[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    i_page_table_entry_invalid: coverpoint ins.current.pte_i[0] {
        // auto fill valid bit 0/1
    }
    d_virt_adr_misaligned: coverpoint ins.current.virt_adr_d[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    d_page_table_entry_invalid: coverpoint ins.current.pte_d[0] {
        // auto fill valid bit 0/1
    }
    memops: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
        wildcard bins lw = {LW};
    }
    medeleg_walk: coverpoint ins.current.csr[CSR_MEDELEG] {
        bins zeros                    = {16'b0000_0000_0000_0000};
        `ifndef ZCA_SUPPORTED
            bins instrmisaligned_enabled = {16'b0000_0000_0000_0001};
        `endif
        bins illegalinstr_enabled     = {16'b0000_0000_0000_0100};
        bins breakpoint_enabled       = {16'b0000_0000_0000_1000};
        bins loadmisaligned_enabled   = {16'b0000_0000_0001_0000};
        bins storemisaligned_enabled  = {16'b0000_0000_0100_0000};
        bins ecallu_enabled           = {16'b0000_0001_0000_0000};
        // Delegating ecall to S mode makes it impossible to escape S mode
        // bins ecalls_enabled           = {16'b0000_0010_0000_0000};
        // bit 10 reserved
        // bit 11 is read only zero
        bins instrpagefault_enabled   = {16'b0001_0000_0000_0000};
        bins loadpagefault_enabled    = {16'b0010_0000_0000_0000};
        // bit 14 reserved
        bins storepagefault_enabled   = {16'b1000_0000_0000_0000};
        wildcard bins ones            = {16'b1011_0001_?1?1_11??}; // access faults might not be possible to delegate if they don't exist
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
            bins instraccessfault_enabled = {16'b0000_0000_0000_0010};
            bins loadaccessfault_enabled  = {16'b0000_0000_0010_0000};
            bins storeaccessfault_enabled = {16'b0000_0000_1000_0000};
        `endif
    }
    jalr: coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }

    // Main Coverpoints
    // Test M mode fetches using an identity mapped Virtual Address with V=0. No translation for instruction fetches and V=0 won't be checked, therefore it must not fault
    cp_instr_page_fault_m: cross priv_mode_m, mstatus_mprv_one, mstatus_mpp, jalr;
    cp_load_page_fault_m:  cross priv_mode_m, mstatus_mprv_one, mstatus_mpp, load_page_fault;
    cp_store_page_fault_m: cross priv_mode_m, mstatus_mprv_one, mstatus_mpp, store_page_fault;
    cp_medeleg_m:          cross priv_mode_m, memops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_fetch_m:    cross priv_mode_m, jalr,   i_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_s:          cross priv_mode_s, memops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_fetch_s:    cross priv_mode_s, jalr,   i_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_u:          cross priv_mode_u, memops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_fetch_u:    cross priv_mode_u, jalr,   i_page_table_entry_invalid, medeleg_walk;

    // Access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            i_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_i[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
            d_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_d[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            i_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_i[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
            d_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_d[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_misaligned_priority_m:       cross priv_mode_m, memops, d_virt_adr_misaligned, d_phys_address_nonexistent, d_page_table_entry_invalid;
        cp_misaligned_priority_fetch_m: cross priv_mode_m, jalr,   i_phys_adr_misaligned, i_phys_address_nonexistent, i_page_table_entry_invalid, mstatus_mprv_one, mstatus_mpp;
    `endif
endgroup

function void exceptionssvsm_sample(int hart, int issue, ins_t ins);
    ExceptionsSvSm_cg.sample(ins);
endfunction
