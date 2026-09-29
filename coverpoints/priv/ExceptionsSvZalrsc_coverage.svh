///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 25 March 2025
//          David_Harris@hmc.edu 11 June 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSSVZALRSC
covergroup ExceptionsSvZalrsc_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    d_virt_adr_misaligned: coverpoint ins.current.virt_adr_d[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    d_page_table_entry_invalid: coverpoint ins.current.pte_d[0] {
        // auto fill valid bit 0/1
    }
    lrscops: coverpoint ins.current.insn {
        wildcard bins lr_w     = {LR_W};
        wildcard bins sc_w     = {SC_W};
    }
    // main coverpoints

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            d_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_d[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            d_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_d[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_misaligned_priority_s:        cross priv_mode_s, lrscops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                // The misaligned exception is raised before translation, so there is no PTE or physical address
                ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
            `endif
        }
        cp_misaligned_priority_u:        cross priv_mode_u, lrscops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                // The misaligned exception is raised before translation, so there is no PTE or physical address
                ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
            `endif
        }
    `endif
endgroup

function void exceptionssvzalrsc_sample(int hart, int issue, ins_t ins);
    ExceptionsSvZalrsc_cg.sample(ins);
endfunction
