///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVPBMT
covergroup Svpbmt_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    nonleaf_PTE_pbmt_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins pbmt_1 = {8'b00?00001} iff (ins.current.pte_i[62:61] == 2'b01);
        wildcard bins pbmt_2 = {8'b00?00001} iff (ins.current.pte_i[62:61] == 2'b10);
        wildcard bins pbmt_3 = {8'b00?00001} iff (ins.current.pte_i[62:61] == 2'b11);
    }
    nonleaf_PTE_pbmt_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins pbmt_1 = {8'b00?00001} iff (ins.current.pte_d[62:61] == 2'b01);
        wildcard bins pbmt_2 = {8'b00?00001} iff (ins.current.pte_d[62:61] == 2'b10);
        wildcard bins pbmt_3 = {8'b00?00001} iff (ins.current.pte_d[62:61] == 2'b11);
    }

    leaf_PTE_pbmt_s_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins pbmt_1 = {8'b11?01111} iff (ins.current.pte_i[62:61] == 2'b01);
        wildcard bins pbmt_2 = {8'b11?01111} iff (ins.current.pte_i[62:61] == 2'b10);
    }
    leaf_PTE_pbmt_u_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins pbmt_1 = {8'b11?11111} iff (ins.current.pte_i[62:61] == 2'b01);
        wildcard bins pbmt_2 = {8'b11?11111} iff (ins.current.pte_i[62:61] == 2'b10);
    }
    leaf_PTE_pbmt_s_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins pbmt_1 = {8'b11?01111} iff (ins.current.pte_d[62:61] == 2'b01);
        wildcard bins pbmt_2 = {8'b11?01111} iff (ins.current.pte_d[62:61] == 2'b10);
    }
    leaf_PTE_pbmt_u_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins pbmt_1 = {8'b11?11111} iff (ins.current.pte_d[62:61] == 2'b01);
        wildcard bins pbmt_2 = {8'b11?11111} iff (ins.current.pte_d[62:61] == 2'b10);
    }

    leaf_PTE_pbmt_res_s_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins pbmt_3 = {8'b11?01111} iff (ins.current.pte_i[62:61] == 2'b11);
    }
    leaf_PTE_pbmt_res_u_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins pbmt_3 = {8'b11?11111} iff (ins.current.pte_i[62:61] == 2'b11);
    }
    leaf_PTE_pbmt_res_s_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins pbmt_3 = {8'b11?01111} iff (ins.current.pte_d[62:61] == 2'b11);
    }
    leaf_PTE_pbmt_res_u_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins pbmt_3 = {8'b11?11111} iff (ins.current.pte_d[62:61] == 2'b11);
    }

    PBMTE_set: coverpoint ins.current.csr[12'h30A][62] {
            bins PBMTE_set = {1'b1};
    }

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

    jalr: coverpoint ins.prev.insn {
        wildcard bins jalr = {32'b????????????_?????_000_?????_1100111};
    }
    lw: coverpoint ins.current.insn {
        wildcard bins lw = {32'b????????????_?????_010_?????_0000011};
    }
    sw: coverpoint ins.current.insn {
        wildcard bins sw = {32'b????????????_?????_010_?????_0100011};
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

    nonleaf_PTE_pbmt_exec_s:  cross nonleaf_PTE_pbmt_i, PBMTE_set, PageType_i, jalr, ins_page_fault, priv_mode_s {
        `ifdef SV39     ignore_bins ig1 = binsof(PageType_i.sv39_kilo); `endif
        `ifdef SV48     ignore_bins ig2 = binsof(PageType_i.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_exec_u:  cross nonleaf_PTE_pbmt_i, PBMTE_set, PageType_i, jalr, ins_page_fault, priv_mode_u {
        `ifdef SV39     ignore_bins ig1 = binsof(PageType_i.sv39_kilo); `endif
        `ifdef SV48     ignore_bins ig2 = binsof(PageType_i.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_read_s:  cross nonleaf_PTE_pbmt_d, PBMTE_set, PageType_d, lw, load_page_fault, priv_mode_s {
        `ifdef SV39     ignore_bins ig1 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef SV48     ignore_bins ig2 = binsof(PageType_d.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_read_u:  cross nonleaf_PTE_pbmt_d, PBMTE_set, PageType_d, lw, load_page_fault, priv_mode_u {
        `ifdef SV39     ignore_bins ig1 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef SV48     ignore_bins ig2 = binsof(PageType_d.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_write_s: cross nonleaf_PTE_pbmt_d, PBMTE_set, PageType_d, sw, store_page_fault, priv_mode_s {
        `ifdef SV39     ignore_bins ig1 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef SV48     ignore_bins ig2 = binsof(PageType_d.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_write_u: cross nonleaf_PTE_pbmt_d, PBMTE_set, PageType_d, sw, store_page_fault, priv_mode_u {
        `ifdef SV39     ignore_bins ig1 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef SV48     ignore_bins ig2 = binsof(PageType_d.sv48_kilo); `endif
    }

    leaf_PTE_pbmt_exec_s:  cross leaf_PTE_pbmt_s_i, PBMTE_set, PageType_i, jalr, priv_mode_s;
    leaf_PTE_pbmt_exec_u:  cross leaf_PTE_pbmt_u_i, PBMTE_set, PageType_i, jalr, priv_mode_u;
    leaf_PTE_pbmt_read_s:  cross leaf_PTE_pbmt_s_d, PBMTE_set, PageType_d, lw, priv_mode_s;
    leaf_PTE_pbmt_read_u:  cross leaf_PTE_pbmt_u_d, PBMTE_set, PageType_d, lw, priv_mode_u;
    leaf_PTE_pbmt_write_s: cross leaf_PTE_pbmt_s_d, PBMTE_set, PageType_d, sw, priv_mode_s;
    leaf_PTE_pbmt_write_u: cross leaf_PTE_pbmt_u_d, PBMTE_set, PageType_d, sw, priv_mode_u;

    leaf_PTE_pbmt_reserved_enc_exec_s:  cross leaf_PTE_pbmt_res_s_i, PBMTE_set, PageType_i, jalr, ins_page_fault, priv_mode_s;
    leaf_PTE_pbmt_reserved_enc_exec_u:  cross leaf_PTE_pbmt_res_u_i, PBMTE_set, PageType_i, jalr, ins_page_fault, priv_mode_u;
    leaf_PTE_pbmt_reserved_enc_read_s:  cross leaf_PTE_pbmt_res_s_d, PBMTE_set, PageType_d, lw, load_page_fault, priv_mode_s;
    leaf_PTE_pbmt_reserved_enc_read_u:  cross leaf_PTE_pbmt_res_u_d, PBMTE_set, PageType_d, lw, load_page_fault, priv_mode_u;
    leaf_PTE_pbmt_reserved_enc_write_s: cross leaf_PTE_pbmt_res_s_d, PBMTE_set, PageType_d, sw, store_page_fault, priv_mode_s;
    leaf_PTE_pbmt_reserved_enc_write_u: cross leaf_PTE_pbmt_res_u_d, PBMTE_set, PageType_d, sw, store_page_fault, priv_mode_u;

endgroup

function void svpbmt_sample(int hart, int issue, ins_t ins);
    Svpbmt_cg.sample(ins);
endfunction
