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

    instr_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") == `UDB_MXLEN'(INSTRUCTION_PAGE_FAULT)) {
        // auto fill 0/1
    }
    load_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") == `UDB_MXLEN'(LOAD_PAGE_FAULT)) {
        // auto fill 0/1
    }
    store_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") == `UDB_MXLEN'(STORE_AMO_PAGE_FAULT)) {
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
    jalr_cross: coverpoint ((ins.current.insn ==? JALR) | (ins.prev.insn ==? JALR)) {
        bins jalr = {1'b1};
    }

    // A fetch, load or store that starts in the last halfword of a page, {scause written, scause, stval[11:0], address[11:0]}
    // (for the fetch, also sepc[11:0], the start of the instruction):
    // it completes, or takes a page fault on the part in the first page (stval at that halfword) or on the part
    // in the second page (stval at its start).  Where both pages fail, the hart reports the part it accesses first.
    `ifdef UDB_MISALIGNED_LDST
        `define EXCEPTIONSSV_CROSS_LOAD
        `define EXCEPTIONSSV_CROSS_STORE
    `elsif UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_LOW
        `ifdef UDB_REPORT_VA_IN_STVAL_ON_LOAD_PAGE_FAULT
            `define EXCEPTIONSSV_CROSS_LOAD
        `endif
        `ifdef UDB_REPORT_VA_IN_STVAL_ON_STORE_AMO_PAGE_FAULT
            `define EXCEPTIONSSV_CROSS_STORE
        `endif
    `endif
    `ifdef EXCEPTIONSSV_CROSS_LOAD
        lw_cross_outcome: coverpoint {ins.current.csr_wb[CSR_SCAUSE], ins.current.csr[CSR_SCAUSE][4:0], ins.current.csr[CSR_STVAL][11:0], ins.current.virt_adr_d[11:0]} {
            `ifdef UDB_MISALIGNED_LDST
                wildcard bins completes     = {30'b0_?????_????????????_111111111110};
            `endif
            `ifdef UDB_REPORT_VA_IN_STVAL_ON_LOAD_PAGE_FAULT
                wildcard bins first_faults  = {30'b1_01101_111111111110_111111111110};
                wildcard bins second_faults = {30'b1_01101_000000000000_111111111110};
            `endif
        }
    `endif
    `ifdef EXCEPTIONSSV_CROSS_STORE
        sw_cross_outcome: coverpoint {ins.current.csr_wb[CSR_SCAUSE], ins.current.csr[CSR_SCAUSE][4:0], ins.current.csr[CSR_STVAL][11:0], ins.current.virt_adr_d[11:0]} {
            `ifdef UDB_MISALIGNED_LDST
                wildcard bins completes     = {30'b0_?????_????????????_111111111110};
            `endif
            `ifdef UDB_REPORT_VA_IN_STVAL_ON_STORE_AMO_PAGE_FAULT
                wildcard bins first_faults  = {30'b1_01111_111111111110_111111111110};
                wildcard bins second_faults = {30'b1_01111_000000000000_111111111110};
            `endif
        }
    `endif
    // The fetch of the jalr target, a 4-byte instruction.  A trace reports a fault on that fetch either in the
    // jalr's own record or in the next one, so jalr_cross accepts the jalr as the current or the previous instruction.
    `ifdef ZCA_SUPPORTED
        jalr_cross_outcome: coverpoint {ins.current.csr_wb[CSR_SCAUSE], ins.current.csr[CSR_SCAUSE][4:0], ins.current.csr[CSR_STVAL][11:0],
                                        ins.current.csr[CSR_SEPC][11:0], ins.current.pc_rdata[11:0]} {
            wildcard bins completes     = {42'b0_?????_????????????_????????????_111111111110};
            `ifdef UDB_REPORT_VA_IN_STVAL_ON_INSTRUCTION_PAGE_FAULT
                wildcard bins first_faults  = {42'b1_01100_111111111110_111111111110_????????????};
                wildcard bins second_faults = {42'b1_01100_000000000000_111111111110_????????????};
            `endif
        }
    `endif


    // Main Coverpoints
    cp_instr_page_fault_s:           cross priv_mode_s, instr_page_fault;
    cp_load_page_fault_s:            cross priv_mode_s, load_page_fault;
    cp_store_page_fault_s:           cross priv_mode_s, store_page_fault;
    // Misaligned accesses that span two pages.  Without misaligned support, a lw or sw with high-priority
    // address-misaligned exceptions never translates; without Zca, the jalr raises instruction-address-misaligned.
    `ifdef EXCEPTIONSSV_CROSS_LOAD
        cp_misaligned_load_page_fault_s:  cross priv_mode_s, lw, lw_cross_outcome;
    `endif
    `ifdef EXCEPTIONSSV_CROSS_STORE
        cp_misaligned_store_page_fault_s: cross priv_mode_s, sw, sw_cross_outcome;
    `endif
    `ifdef ZCA_SUPPORTED
        cp_misaligned_instr_page_fault_s: cross priv_mode_s, jalr_cross, jalr_cross_outcome;
    `endif
    cp_instr_page_fault_u:           cross priv_mode_u, instr_page_fault;
    cp_load_page_fault_u:            cross priv_mode_u, load_page_fault;
    cp_store_page_fault_u:           cross priv_mode_u, store_page_fault;

    // Access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Accesses land at an offset into the faulting region, which is at least 128 bytes
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            i_phys_address_nonexistent: coverpoint ((64'(ins.current.phys_adr_i) - 64'(`RVMODEL_ACCESS_FAULT_ADDRESS)) < 64'd128) {
                // auto fill 1/0 for the physical address being valid
            }
            d_phys_address_nonexistent: coverpoint ((64'(ins.current.phys_adr_d) - 64'(`RVMODEL_ACCESS_FAULT_ADDRESS)) < 64'd128) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            i_phys_address_nonexistent: coverpoint ((64'(ins.current.phys_adr_i) - 64'(`RVMODEL_ACCESS_FAULT_ADDRESS)) < 64'd128) {
                // auto fill 1/0 for the physical address being valid
            }
            d_phys_address_nonexistent: coverpoint ((64'(ins.current.phys_adr_d) - 64'(`RVMODEL_ACCESS_FAULT_ADDRESS)) < 64'd128) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_misaligned_priority_s:        cross priv_mode_s, memops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifndef UDB_MISALIGNED_LDST
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
        cp_misaligned_priority_fetch_s:  cross priv_mode_s, jalr,   i_virt_adr_misaligned, i_page_table_entry_invalid, i_phys_address_nonexistent;
        cp_misaligned_priority_u:        cross priv_mode_u, memops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifndef UDB_MISALIGNED_LDST
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
        cp_misaligned_priority_fetch_u:  cross priv_mode_u, jalr,   i_virt_adr_misaligned, i_page_table_entry_invalid, i_phys_address_nonexistent;
    `endif

endgroup

function void exceptionssv_sample(int hart, int issue, ins_t ins);
    ExceptionsSv_cg.sample(ins);
endfunction
