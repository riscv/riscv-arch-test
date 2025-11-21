///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVADU_PMP
covergroup Svadu_PMP_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    PTE_Abit_unset_s_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins leaflvl_s = {8'b?0?01111};
    }
    PTE_Abit_unset_u_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins leaflvl_u = {8'b?0?11111};
    }
    PTE_Abit_unset_s_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_s = {8'b?0?01111};
    }
    PTE_Abit_unset_u_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b?0?11111};
    }
    PTE_Dbit_unset_s_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_s = {8'b01?0?111};
    }
    PTE_Dbit_unset_u_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b01?1?111};
    }

    `ifdef XLEN64
        PageType_i: coverpoint ins.current.page_type_i {
            `ifdef SV48
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
        }
        PageType_d: coverpoint ins.current.page_type_d {
            `ifdef SV48
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
        }
    `else
        PageType_i: coverpoint ins.current.page_type_i {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31]);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31]);
        }
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31]);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31]);
        }
    `endif

    jalr: coverpoint ins.prev.insn {
        wildcard bins jalr = {32'b????????????_?????_000_?????_1100111};
    }
    lw: coverpoint ins.current.insn {
        wildcard bins lw = {32'b????????????_?????_010_?????_0000011};
    }
    sw: coverpoint ins.current.insn {
        wildcard bins sw = {32'b????????????_?????_010_?????_0100011};
    }
    load_acc_fault: coverpoint  ins.current.csr[12'h342] {
        bins load_acc_fault = {64'd5} iff (ins.current.trap);
    }
    store_acc_fault: coverpoint  ins.current.csr[12'h342] {
        bins store_acc_fault = {64'd7} iff (ins.current.trap);
    }
    ins_acc_fault: coverpoint  ins.current.csr[12'h342] {
        bins ins_acc_fault  = {64'd1} iff (ins.current.trap);
    }

    `ifdef XLEN64
        Svadu_enabled: coverpoint  ins.current.csr[12'h30A][61] {
            bins ADUE_set = {1'b1};
        }
    `else
        Svadu_enabled: coverpoint  ins.current.csr[12'h31A][29] {
            bins ADUE_set = {1'b1};
        }
    `endif

    PMP_pagetable: coverpoint  ins.current.csr[12'h3A0][7:0] {      // PMP permission of page table
        wildcard bins w_unset = {8'b??????01};
    }

    Abit_unset_pmpW_unset_exec_s:  cross PTE_Abit_unset_s_i, PageType_i, Svadu_enabled, PMP_pagetable, jalr, ins_acc_fault, priv_mode_s;
    Abit_unset_pmpW_unset_exec_u:  cross PTE_Abit_unset_u_i, PageType_i, Svadu_enabled, PMP_pagetable, jalr, ins_acc_fault, priv_mode_u;
    Abit_unset_pmpW_unset_read_s:  cross PTE_Abit_unset_s_d, PageType_d, Svadu_enabled, PMP_pagetable, lw, load_acc_fault, priv_mode_s;
    Abit_unset_pmpW_unset_read_u:  cross PTE_Abit_unset_u_d, PageType_d, Svadu_enabled, PMP_pagetable, lw, load_acc_fault, priv_mode_u;
    Abit_unset_pmpW_unset_write_s: cross PTE_Abit_unset_s_d, PageType_d, Svadu_enabled, PMP_pagetable, sw, store_acc_fault, priv_mode_s;
    Abit_unset_pmpW_unset_write_u: cross PTE_Abit_unset_u_d, PageType_d, Svadu_enabled, PMP_pagetable, sw, store_acc_fault, priv_mode_u;
    Dbit_unset_pmpW_unset_write_s: cross PTE_Dbit_unset_s_d, PageType_d, Svadu_enabled, PMP_pagetable, sw, store_acc_fault, priv_mode_s;
    Dbit_unset_pmpW_unset_write_u: cross PTE_Dbit_unset_u_d, PageType_d, Svadu_enabled, PMP_pagetable, sw, store_acc_fault, priv_mode_u;

endgroup

function void svadu_pmp_sample(int hart, int issue, ins_t ins);
    Svadu_PMP_cg.sample(ins);
endfunction
