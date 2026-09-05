///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2026 SiFive, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVUKTEH

covergroup SvukteH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    ukte_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "ukte")[0] {
        bins set = {1};
    }
    ukte_not_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "ukte")[0] {
        bins not_set = {0};
    }

    hukte_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hukte")[0] {
        bins set = {1};
    }
    hukte_not_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hukte")[0] {
        bins not_set = {0};
    }

    // hstatus.SPVP selects the effective privilege of hlv/hlvx/hsv: VU when clear, VS when set.
    spvp_vu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp")[0] {
        bins eff_vu = {0};
    }
    spvp_vs: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp")[0] {
        bins eff_vs = {1};
    }

    // hstatus.HU permits hlv/hlvx/hsv to execute in U-mode.
    hu_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu")[0] {
        bins set = {1};
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

    // With V=1, or for the guest accesses made by hlv/hlvx/hsv, vsatp is the active satp register.
    vsatp_not_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
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

    ins_page_fault: coverpoint  ins.current.csr[CSR_MCAUSE][31:0] {
        bins ins_page_fault = {32'd12} iff (ins.current.trap);
    }
    load_page_fault: coverpoint  ins.current.csr[CSR_MCAUSE][31:0] {
        bins load_page_fault = {32'd13} iff (ins.current.trap);
    }
    store_page_fault: coverpoint  ins.current.csr[CSR_MCAUSE][31:0] {
        bins store_amo_page_fault = {32'd15} iff (ins.current.trap);
    }

    va_high_bit_i: coverpoint ins.current.virt_adr_i[63] {
        bins high = {1'b1};
    }
    no_va_high_bit_i: coverpoint ins.current.virt_adr_i[63] {
        bins high = {1'b0};
    }
    va_high_bit_d: coverpoint ins.current.virt_adr_d[63] {
        bins high = {1'b1};
    }
    no_va_high_bit_d: coverpoint ins.current.virt_adr_d[63] {
        bins high = {1'b0};
    }

    // -----------------------------------------------------------------------
    // HS-Mode Svukte-Qualified Accesses (hlv/hlvx/hsv with hstatus.SPVP=0)
    //
    // The effective privilege of the access is VU even though the hart never
    // leaves HS-mode, so senvcfg.UKTE qualifies it.
    // -----------------------------------------------------------------------

    cp_svukte_qualified_hs_read_fault:  cross ukte_set, priv_mode_hs, spvp_vu, vsatp_not_bare, va_high_bit_d, read_acc,  load_page_fault;
    cp_svukte_qualified_hs_write_fault: cross ukte_set, priv_mode_hs, spvp_vu, vsatp_not_bare, va_high_bit_d, write_acc, store_page_fault;

    // -----------------------------------------------------------------------
    // U-Mode Svukte-Qualified Accesses (hlv/hlvx/hsv with hstatus.HU=1)
    //
    // Crossed with ukte_not_set as well, so hitting these bins proves that
    // hstatus.HUKTE alone qualified the access.
    // -----------------------------------------------------------------------

    cp_svukte_qualified_hukte_read_fault:  cross hukte_set, ukte_not_set, priv_mode_u, hu_set, spvp_vu, vsatp_not_bare, va_high_bit_d, read_acc,  load_page_fault;
    cp_svukte_qualified_hukte_write_fault: cross hukte_set, ukte_not_set, priv_mode_u, hu_set, spvp_vu, vsatp_not_bare, va_high_bit_d, write_acc, store_page_fault;

    // -----------------------------------------------------------------------
    // VU-Mode Svukte-Qualified Accesses
    // -----------------------------------------------------------------------

    cp_svukte_qualified_vu_exec_fault:  cross ukte_set, priv_mode_vu, vsatp_not_bare, va_high_bit_i, exec_acc,  ins_page_fault;
    cp_svukte_qualified_vu_read_fault:  cross ukte_set, priv_mode_vu, vsatp_not_bare, va_high_bit_d, read_acc,  load_page_fault;
    cp_svukte_qualified_vu_write_fault: cross ukte_set, priv_mode_vu, vsatp_not_bare, va_high_bit_d, write_acc, store_page_fault;

    // -----------------------------------------------------------------------
    // Non-Svukte-Qualified Accesses
    // -----------------------------------------------------------------------

    cp_not_svukte_qualified_hs_disabled: cross ukte_not_set, priv_mode_hs, spvp_vu, vsatp_not_bare, va_high_bit_d,    pte_permissive_d, rw_acc;
    cp_not_svukte_qualified_hs_addr:     cross ukte_set,     priv_mode_hs, spvp_vu, vsatp_not_bare, no_va_high_bit_d, pte_permissive_d, rw_acc;
    // Effective privilege VS is never qualified, so the leaf PTE here is a supervisor page.
    cp_not_svukte_qualified_hs_eff_vs:   cross ukte_set,     priv_mode_hs, spvp_vs, vsatp_not_bare, va_high_bit_d,                      rw_acc;

    cp_not_svukte_qualified_hukte_clear: cross hukte_not_set, ukte_set, priv_mode_u, hu_set, spvp_vu, vsatp_not_bare, va_high_bit_d,    pte_permissive_d, rw_acc;
    cp_not_svukte_qualified_hukte_addr:  cross hukte_set,     priv_mode_u, hu_set,   spvp_vu, vsatp_not_bare,         no_va_high_bit_d, pte_permissive_d, rw_acc;

    cp_not_svukte_qualified_vu_disabled:   cross ukte_not_set, priv_mode_vu, vsatp_not_bare, va_high_bit_d,    pte_permissive_d, rw_acc;
    cp_not_svukte_qualified_vu_addr:       cross ukte_set,     priv_mode_vu, vsatp_not_bare, no_va_high_bit_d, pte_permissive_d, rw_acc;
    cp_not_svukte_qualified_vu_disabled_i: cross ukte_not_set, priv_mode_vu, vsatp_not_bare, va_high_bit_i,    pte_permissive_i, exec_acc;
    cp_not_svukte_qualified_vu_addr_i:     cross ukte_set,     priv_mode_vu, vsatp_not_bare, no_va_high_bit_i, pte_permissive_i, exec_acc;

endgroup

function void svukteh_sample(int hart, int issue, ins_t ins);
    SvukteH_cg.sample(ins);
endfunction
