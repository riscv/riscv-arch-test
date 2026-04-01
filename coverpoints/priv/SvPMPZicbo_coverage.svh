///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVPMPZICBO
covergroup SvPMPZicbo_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    // All PTE permissions
    PTE_s: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    PTE_u: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b11?11111};
    }

    `ifdef XLEN64
        PageType_d: coverpoint ins.current.page_type_d {
            `ifdef SV48_SUPPORTED
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
    }
    `else
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
        }
    `endif

    store_acc_fault: coverpoint  ins.current.csr[12'h342] {
        bins store_acc_fault = {64'd7};
    }

    cbo_ins: coverpoint ins.current.insn {
        `ifdef ZICBOM_SUPPORTED
            wildcard bins any_zicbom_ins = {CBO_INVAL, CBO_CLEAN, CBO_FLUSH};
        `endif
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins zicboz_ins = {CBO_ZERO};
        `endif
    }

    PMP_perm: coverpoint  ins.current.csr[12'h3A0][7:0] {
        wildcard bins rw_unset   = {8'b?????100};
    }


    cp_PA_PMP_rw_unset_cbo_s:  cross PTE_s, PageType_d, PMP_perm, cbo_ins, store_acc_fault, priv_mode_s;
    cp_PA_PMP_rw_unset_cbo_u:  cross PTE_u, PageType_d, PMP_perm, cbo_ins, store_acc_fault, priv_mode_u;
    cp_PTE_PMP_rw_unset_cbo_s: cross PTE_s, PageType_d, PMP_perm, cbo_ins, store_acc_fault, priv_mode_s;
    cp_PTE_PMP_rw_unset_cbo_u: cross PTE_u, PageType_d, PMP_perm, cbo_ins, store_acc_fault, priv_mode_u;

endgroup

function void svpmpzicbo_sample(int hart, int issue, ins_t ins);
    SvPMPZicbo_cg.sample(ins);
endfunction
