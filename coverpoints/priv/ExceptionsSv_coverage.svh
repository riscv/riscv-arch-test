///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 25 March 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSSV
covergroup ExceptionsSv_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    instr_page_fault: coverpoint (ins.current.csr[CSR_SCAUSE][31:0] == 32'd12) {
        // auto fill 0/1
    }
    load_page_fault: coverpoint (ins.current.csr[CSR_SCAUSE][31:0] == 32'd13) {
        // auto fill 0/1
    }
    store_page_fault: coverpoint (ins.current.csr[CSR_SCAUSE][31:0] == 32'd15) {
        // auto fill 0/1
    }
    // The PC of the target: a fetch that spans two parcels may report either parcel in virt_adr_i
    i_virt_adr_misaligned: coverpoint ins.current.pc_rdata[1:0] {
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
        wildcard bins sw       = {SW};
        wildcard bins lw       = {LW};
    }
    lw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    sw: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }
    jalr: coverpoint ins.prev.insn {
        wildcard bins jalr = {JALR};
    }

    d_page_table_entry_bad: coverpoint ins.current.pte_d[7:0] {
        bins invalid = {8'b00000000}; // invalid
    }

    d_phys_address: coverpoint ins.current.phys_adr_d[11:0] {
        // check that fault occurs on the last halfword of the first page and the first halfword of the second page
        bins first  = {12'b111111111110};
        bins second = {12'b000000000000};
    }

    i_page_table_entry_bad: coverpoint ins.current.pte_i[7:0] {
        bins invalid = {8'b00000000}; // invalid
    }

    i_phys_address: coverpoint ins.current.phys_adr_i[11:0] {
        // check that fault occurs on the last halfword of the first page and the first halfword of the second page
        bins first  = {12'b111111111110};
        bins second = {12'b000000000000};
    }


    // Main Coverpoints
    cp_instr_page_fault_s:           cross priv_mode_s, instr_page_fault;
    cp_load_page_fault_s:            cross priv_mode_s, load_page_fault;
    cp_store_page_fault_s:           cross priv_mode_s, store_page_fault;
    cp_misaligned_load_page_fault_s: cross priv_mode_s, d_page_table_entry_bad, d_phys_address, lw;
    cp_misaligned_store_page_fault_s:cross priv_mode_s, d_page_table_entry_bad, d_phys_address, sw;
    cp_misaligned_inst_page_fault_s: cross priv_mode_s, i_page_table_entry_bad, i_phys_address, jalr;
    cp_instr_page_fault_u:           cross priv_mode_u, instr_page_fault;
    cp_load_page_fault_u:            cross priv_mode_u, load_page_fault;
    cp_store_page_fault_u:           cross priv_mode_u, store_page_fault;

    // Access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Accesses land at an offset into the faulting region, which is at least 128 bytes
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            i_phys_address_nonexistent: coverpoint ((ins.current.phys_adr_i - `RVMODEL_ACCESS_FAULT_ADDRESS) < 128) {
                // auto fill 1/0 for the physical address being valid
            }
            d_phys_address_nonexistent: coverpoint ((ins.current.phys_adr_d - `RVMODEL_ACCESS_FAULT_ADDRESS) < 128) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            i_phys_address_nonexistent: coverpoint ((ins.current.phys_adr_i - `RVMODEL_ACCESS_FAULT_ADDRESS) < 128) {
                // auto fill 1/0 for the physical address being valid
            }
            d_phys_address_nonexistent: coverpoint ((ins.current.phys_adr_d - `RVMODEL_ACCESS_FAULT_ADDRESS) < 128) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_misaligned_priority_s:        cross priv_mode_s, memops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent;
        cp_misaligned_priority_fetch_s:  cross priv_mode_s, jalr,   i_virt_adr_misaligned, i_page_table_entry_invalid, i_phys_address_nonexistent;
        cp_misaligned_priority_u:        cross priv_mode_u, memops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent;
        cp_misaligned_priority_fetch_u:  cross priv_mode_u, jalr,   i_virt_adr_misaligned, i_page_table_entry_invalid, i_phys_address_nonexistent;
    `endif

endgroup

function void exceptionssv_sample(int hart, int issue, ins_t ins);
    ExceptionsSv_cg.sample(ins);
endfunction
