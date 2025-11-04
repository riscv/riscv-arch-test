///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVNAPOT
covergroup Svnapot_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "coverage/RISCV_coverage_standard_coverpoints.svh"

    PTE_N_i: coverpoint ins.current.pte_i[63] {
        bins pte_N_set = {1'b1};
    }
    PTE_N_d: coverpoint ins.current.pte_d[63] {
        bins pte_N_set = {1'b1};
    }
    PTE_RWX_s_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    PTE_RWX_u_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins leaflvl_u = {8'b11?11111};
    }
    PTE_RWX_s_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    PTE_RWX_u_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b11?11111};
    }

    PTE_Svnapot_i: coverpoint ins.current.pte_i[13:10] {
        wildcard bins svnapot_enc = {4'b1000};
    }
    PTE_Svnapot_d: coverpoint ins.current.pte_d[13:10] {
        wildcard bins svnapot_enc = {4'b1000};
    }

    PTE_Svnapot_reserved_enc_i: coverpoint ins.current.pte_i[13:10] {
        wildcard bins reserved_xxx1 = {4'b???1};
        wildcard bins reserved_xx1x = {4'b??1?};
        wildcard bins reserved_x1xx = {4'b?1??};
        wildcard bins reserved_0xxx = {4'b0???};
    }
    PTE_Svnapot_reserved_enc_d: coverpoint ins.current.pte_d[13:10] {
        wildcard bins reserved_xxx1 = {4'b???1};
        wildcard bins reserved_xx1x = {4'b??1?};
        wildcard bins reserved_x1xx = {4'b?1??};
        wildcard bins reserved_0xxx = {4'b0???};
    }

    PageType_i: coverpoint ins.current.page_type_i {
        `ifdef SV48
            bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
        `endif
        `ifdef SV39
            bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
        `endif
    }
    PageType_d: coverpoint ins.current.page_type_d {
        `ifdef SV48
            bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
        `endif
        `ifdef SV39
            bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
        `endif
    }

    mode: coverpoint ins.current.csr[12'h180][63:60] {
        `ifdef SV57
            bins sv57 = {4'b1010};
        `endif
        `ifdef SV48
            bins sv48 = {4'b1001};
        `endif
        `ifdef SV39
            bins sv39 = {4'b1000};
        `endif
    }
    kilopage_i: coverpoint ins.current.page_type_i {
        bins kilo = {2'b00};
    }
    kilopage_d: coverpoint ins.current.page_type_d {
        bins kilo = {2'b00};
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

    ins_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins ins_page_fault = {32'd12} iff (ins.current.trap);
    }
    load_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins load_page_fault = {32'd13} iff (ins.current.trap);
    }
    store_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins store_amo_page_fault = {32'd15} iff (ins.current.trap);
    }

    Svnapot_legal_enc_exec_s:  cross PTE_RWX_s_i, PTE_Svnapot_i, PTE_N_i, kilopage_i, mode, exec_acc, priv_mode_s;
    Svnapot_legal_enc_exec_u:  cross PTE_RWX_u_i, PTE_Svnapot_i, PTE_N_i, kilopage_i, mode, exec_acc, priv_mode_u;
    Svnapot_legal_enc_read_s:  cross PTE_RWX_s_d, PTE_Svnapot_d, PTE_N_d, kilopage_d, mode, read_acc, priv_mode_s;
    Svnapot_legal_enc_read_u:  cross PTE_RWX_u_d, PTE_Svnapot_d, PTE_N_d, kilopage_d, mode, read_acc, priv_mode_u;
    Svnapot_legal_enc_write_s: cross PTE_RWX_s_d, PTE_Svnapot_d, PTE_N_d, kilopage_d, mode, write_acc, priv_mode_s;
    Svnapot_legal_enc_write_u: cross PTE_RWX_u_d, PTE_Svnapot_d, PTE_N_d, kilopage_d, mode, write_acc, priv_mode_u;

    Svnapot_reserved_enc_exec_s:  cross PTE_RWX_s_i, PTE_Svnapot_reserved_enc_i, PTE_N_i, kilopage_i, mode, exec_acc, ins_page_fault, priv_mode_s;
    Svnapot_reserved_enc_exec_u:  cross PTE_RWX_u_i, PTE_Svnapot_reserved_enc_i, PTE_N_i, kilopage_i, mode, exec_acc, ins_page_fault, priv_mode_u;
    Svnapot_reserved_enc_read_s:  cross PTE_RWX_s_d, PTE_Svnapot_reserved_enc_d, PTE_N_d, kilopage_d, mode, read_acc, load_page_fault, priv_mode_s;
    Svnapot_reserved_enc_read_u:  cross PTE_RWX_u_d, PTE_Svnapot_reserved_enc_d, PTE_N_d, kilopage_d, mode, read_acc, load_page_fault, priv_mode_u;
    Svnapot_reserved_enc_write_s: cross PTE_RWX_s_d, PTE_Svnapot_reserved_enc_d, PTE_N_d, kilopage_d, mode, write_acc, store_page_fault, priv_mode_s;
    Svnapot_reserved_enc_write_u: cross PTE_RWX_u_d, PTE_Svnapot_reserved_enc_d, PTE_N_d, kilopage_d, mode, write_acc, store_page_fault, priv_mode_u;

    Svnapot_reserved_ppni_exec_s:  cross PTE_RWX_s_i, PTE_N_i, PageType_i, exec_acc, ins_page_fault, priv_mode_s;
    Svnapot_reserved_ppni_exec_u:  cross PTE_RWX_u_i, PTE_N_i, PageType_i, exec_acc, ins_page_fault, priv_mode_u;
    Svnapot_reserved_ppni_read_s:  cross PTE_RWX_s_d, PTE_N_d, PageType_d, read_acc, load_page_fault, priv_mode_s;
    Svnapot_reserved_ppni_read_u:  cross PTE_RWX_u_d, PTE_N_d, PageType_d, read_acc, load_page_fault, priv_mode_u;
    Svnapot_reserved_ppni_write_s: cross PTE_RWX_s_d, PTE_N_d, PageType_d, write_acc, store_page_fault, priv_mode_s;
    Svnapot_reserved_ppni_write_u: cross PTE_RWX_u_d, PTE_N_d, PageType_d, write_acc, store_page_fault, priv_mode_u;

endgroup

function void svnapot_sample(int hart, int issue, ins_t ins);
    Svnapot_cg.sample(ins);
endfunction
