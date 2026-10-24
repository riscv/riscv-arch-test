///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVADU
covergroup Svadu_cg with function sample(ins_t ins);
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

    `ifdef UDB_MXLEN_64
        PageType_i: coverpoint ins.current.page_type_i {
            `ifdef SV48_SUPPORTED
                bins sv48_tera = {2'b11} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
            `endif
        }
        PageType_d: coverpoint ins.current.page_type_d {
            `ifdef SV48_SUPPORTED
                bins sv48_tera = {2'b11} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
            `endif
        }
    `else
        PageType_i: coverpoint ins.current.page_type_i {
            bins sv32_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0]);
            bins sv32_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0]);
        }
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0]);
            bins sv32_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0]);
        }
    `endif

    // A=0 leaf PTEs whose access must page fault before any A/D update
    PTE_fault_reason_i: coverpoint ins.current.pte_i[6] {
        bins upage           = {1'b0} iff (ins.current.pte_i[4]);
        bins reserved_rwx    = {1'b0} iff (ins.current.pte_i[2:1] == 2'b10);
        `ifdef UDB_MXLEN_64
            bins reserved_bits   = {1'b0} iff (ins.current.pte_i[60:54] != 0);
            bins pbmt_reserved   = {1'b0} iff (ins.current.pte_i[62:61] == 2'b11);
            bins napot_reserved  = {1'b0} iff (ins.current.pte_i[63] & ((ins.current.pte_i[13:10] != 4'b1000) | (ins.current.page_type_i != 0)));
            bins misaligned_page = {1'b0} iff (((ins.current.page_type_i == 2'b01) & (ins.current.pte_i[18:10] != 0)) |
                                                 ((ins.current.page_type_i == 2'b10) & (ins.current.pte_i[27:10] != 0)) |
                                                 ((ins.current.page_type_i == 2'b11) & (ins.current.pte_i[36:10] != 0)));
        `else
            bins misaligned_page = {1'b0} iff ((ins.current.page_type_i == 2'b01) & (ins.current.pte_i[19:10] != 0));
        `endif
    }
    // A=0 leaf PTEs whose access must page fault before any A/D update
    PTE_fault_reason_d: coverpoint ins.current.pte_d[6] {
        bins upage           = {1'b0} iff (ins.current.pte_d[4]);
        bins reserved_rwx    = {1'b0} iff (ins.current.pte_d[2:1] == 2'b10);
        `ifdef UDB_MXLEN_64
            bins reserved_bits   = {1'b0} iff (ins.current.pte_d[60:54] != 0);
            bins pbmt_reserved   = {1'b0} iff (ins.current.pte_d[62:61] == 2'b11);
            bins napot_reserved  = {1'b0} iff (ins.current.pte_d[63] & ((ins.current.pte_d[13:10] != 4'b1000) | (ins.current.page_type_d != 0)));
            bins misaligned_page = {1'b0} iff (((ins.current.page_type_d == 2'b01) & (ins.current.pte_d[18:10] != 0)) |
                                                 ((ins.current.page_type_d == 2'b10) & (ins.current.pte_d[27:10] != 0)) |
                                                 ((ins.current.page_type_d == 2'b11) & (ins.current.pte_d[36:10] != 0)));
        `else
            bins misaligned_page = {1'b0} iff ((ins.current.page_type_d == 2'b01) & (ins.current.pte_d[19:10] != 0));
        `endif
    }

    ins_page_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins ins_page_fault = {INSTRUCTION_PAGE_FAULT} iff (ins.current.trap);
    }
    load_page_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins load_page_fault = {LOAD_PAGE_FAULT} iff (ins.current.trap);
    }
    store_page_fault: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins store_amo_page_fault = {STORE_AMO_PAGE_FAULT} iff (ins.current.trap);
    }

    exec_acc: coverpoint ins.current.execute_access {
        bins set = {1};
    }
    read_acc: coverpoint ins.current.read_access {
        bins set = {1};
    }
    write_acc: coverpoint ins.current.write_access{
        bins set = {1};
    }

    `ifdef UDB_MXLEN_64
        Svadu_enabled: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "adue")[0] {
            bins ADUE_set = {1'b1};
        }
    `else
        Svadu_enabled: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfgh", "adue")[0] {
            bins ADUE_set = {1'b1};
        }
    `endif

    Abit_unset_exec_s:  cross PTE_Abit_unset_s_i, PageType_i, Svadu_enabled, exec_acc, priv_mode_s;
    Abit_unset_exec_u:  cross PTE_Abit_unset_u_i, PageType_i, Svadu_enabled, exec_acc, priv_mode_u;
    Abit_unset_read_s:  cross PTE_Abit_unset_s_d, PageType_d, Svadu_enabled, read_acc, priv_mode_s;
    Abit_unset_read_u:  cross PTE_Abit_unset_u_d, PageType_d, Svadu_enabled, read_acc, priv_mode_u;
    Abit_unset_write_s: cross PTE_Abit_unset_s_d, PageType_d, Svadu_enabled, write_acc, priv_mode_s;
    Abit_unset_write_u: cross PTE_Abit_unset_u_d, PageType_d, Svadu_enabled, write_acc, priv_mode_u;
    Dbit_unset_write_s: cross PTE_Dbit_unset_s_d, PageType_d, Svadu_enabled, write_acc, priv_mode_s;
    Dbit_unset_write_u: cross PTE_Dbit_unset_u_d, PageType_d, Svadu_enabled, write_acc, priv_mode_u;

    fault_no_update_exec_s:  cross PTE_fault_reason_i, Svadu_enabled, exec_acc, ins_page_fault, priv_mode_s;
    fault_no_update_read_s:  cross PTE_fault_reason_d, Svadu_enabled, read_acc, load_page_fault, priv_mode_s;
    fault_no_update_write_s: cross PTE_fault_reason_d, Svadu_enabled, write_acc, store_page_fault, priv_mode_s;

endgroup

function void svadu_sample(int hart, int issue, ins_t ins);
    Svadu_cg.sample(ins);
endfunction
