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

`define COVER_EXCEPTIONSVMZAAMO
covergroup ExceptionsVMZaamo_cg with function sample(ins_t ins);
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
    `ifdef XLEN64 // Number of physical address bits is different by XLEN, either 34 or 56
        d_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_d[55:2], 2'b00} == `ACCESS_FAULT_ADDRESS) {
            // auto fill 1/0 for the physical address being valid
        }
    `else
        d_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_d[33:2], 2'b00} == `ACCESS_FAULT_ADDRESS) {
            // auto fill 1/0 for the physical address being valid
        }
    `endif
    amemops: coverpoint ins.current.insn {
        wildcard bins amoadd_w = {32'b0000000_?????_?????_010_?????_0101111};
    }
    medeleg_walk: coverpoint ins.current.csr[12'h302] {
        bins zeros                    = {16'b0000_0000_0000_0000};
        `ifndef COVER_ZCA
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
        wildcard bins ones            = {16'b1011_0001_1111_111?};
    }

    // main coverpoints
    cp_misaligned_priority_m:        cross priv_mode_m, amemops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent;
    cp_medeleg_m:                    cross priv_mode_m, amemops,  d_page_table_entry_invalid, medeleg_walk;
    cp_misaligned_priority_s:        cross priv_mode_s, amemops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent;
    cp_medeleg_s:                    cross priv_mode_s, amemops, d_page_table_entry_invalid, medeleg_walk;
    cp_misaligned_priority_u:        cross priv_mode_u, amemops,  d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent;
    cp_medeleg_u:                    cross priv_mode_u, amemops,  d_page_table_entry_invalid, medeleg_walk;

endgroup

function void exceptionsvmzaamo_sample(int hart, int issue, ins_t ins);
    ExceptionsVMZaamo_cg.sample(ins);
endfunction
