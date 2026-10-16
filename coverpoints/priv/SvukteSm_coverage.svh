///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2026 SiFive, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVUKTESM

covergroup SvukteSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    ukte_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "ukte") {
        bins set = {1};
    }
    ukte_not_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "ukte") {
        bins not_set = {0};
    }
    no_trap: coverpoint ins.current.trap {
        bins success = {0};
    }

    exec_acc: coverpoint ins.current.execute_access {
        bins set = {1};
    }
    read_acc: coverpoint ins.current.read_access {
        bins set = {1};
    }
    write_acc: coverpoint ins.current.write_access {
        bins set = {1};
    }
    rw_acc: coverpoint (ins.current.write_access | ins.current.read_access) {
        bins set = {1};
    }

    pte_permissive_i: coverpoint ins.current.pte_i[7:0] {
        // Ensures the leaf page is readable, executable and user-accessible.
        wildcard bins user_rx = {8'b???11?11};
    }
    pte_permissive_d: coverpoint ins.current.pte_d[7:0] {
        // Ensures the leaf page is readable, writable and user-accessible.
        wildcard bins user_rw = {8'b???1?111};
    }

    mprv_mstatus_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins set = {1'b1};
    }
    mprv_mstatus_not_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins not_set = {1'b0};
    }
    mpp_mstatus_u: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        bins u_mode = {2'b00};
    }

    satp_not_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
        // At least one of these should always be active, as Svukte requires Sv39.
        `ifdef SV39_SUPPORTED
            bins sv39 = {4'b1000};
        `endif
        `ifdef SV48_SUPPORTED
            bins sv48 = {4'b1001};
        `endif
        `ifdef SV57_SUPPORTED
            bins sv57 = {4'b1010};
        `endif
    }

    load_page_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins load_page_fault = {LOAD_PAGE_FAULT} iff (ins.current.trap);
    }
    store_page_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins store_amo_page_fault = {STORE_AMO_PAGE_FAULT} iff (ins.current.trap);
    }

    va_high_bit_i: coverpoint ins.current.virt_adr_i[63] {
        bins high = {1'b1};
    }
    va_high_bit_d: coverpoint ins.current.virt_adr_d[63] {
        bins high = {1'b1};
    }

    // -----------------------------------------------------------------------
    // Machine Svukte-Qualified Accesses (using MPRV)
    // -----------------------------------------------------------------------

    cp_svukte_qualified_mprv_read_fault:  cross ukte_set, priv_mode_m, mprv_mstatus_set, mpp_mstatus_u, satp_not_bare, va_high_bit_d, read_acc,  load_page_fault;
    cp_svukte_qualified_mprv_write_fault: cross ukte_set, priv_mode_m, mprv_mstatus_set, mpp_mstatus_u, satp_not_bare, va_high_bit_d, write_acc, store_page_fault;

    // -----------------------------------------------------------------------
    // Effective U-mode accesses with UKTE clear
    // -----------------------------------------------------------------------

    cp_not_svukte_qualified_mprv_read:  cross ukte_not_set, priv_mode_m, mprv_mstatus_set, mpp_mstatus_u, satp_not_bare, va_high_bit_d, pte_permissive_d, read_acc, no_trap;
    cp_not_svukte_qualified_mprv_write: cross ukte_not_set, priv_mode_m, mprv_mstatus_set, mpp_mstatus_u, satp_not_bare, va_high_bit_d, pte_permissive_d, write_acc, no_trap;

endgroup

function void svuktesm_sample(int hart, int issue, ins_t ins);
    SvukteSm_cg.sample(ins);
endfunction
