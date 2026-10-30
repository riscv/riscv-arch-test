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

    PBMTE_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "pbmte")[0] {
            bins PBMTE_set = {1'b1};
    }

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

    jalr: coverpoint ins.prev.insn {
        wildcard bins jalr = {JALR};
    }
    lw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    sw: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }

    ins_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins ins_page_fault = {INSTRUCTION_PAGE_FAULT} iff (ins.current.trap);
    }
    load_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins load_page_fault = {LOAD_PAGE_FAULT} iff (ins.current.trap);
    }
    store_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins store_amo_page_fault = {STORE_AMO_PAGE_FAULT} iff (ins.current.trap);
    }

    nonleaf_PTE_pbmt_exec_s:  cross nonleaf_PTE_pbmt_i, PBMTE_set, PageType_i, jalr, ins_page_fault, priv_mode_s {
        `ifdef SV39_SUPPORTED     ignore_bins ig1 = binsof(PageType_i.sv39_kilo); `endif
        `ifdef SV48_SUPPORTED     ignore_bins ig2 = binsof(PageType_i.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_exec_u:  cross nonleaf_PTE_pbmt_i, PBMTE_set, PageType_i, jalr, ins_page_fault, priv_mode_u {
        `ifdef SV39_SUPPORTED     ignore_bins ig1 = binsof(PageType_i.sv39_kilo); `endif
        `ifdef SV48_SUPPORTED     ignore_bins ig2 = binsof(PageType_i.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_read_s:  cross nonleaf_PTE_pbmt_d, PBMTE_set, PageType_d, lw, load_page_fault, priv_mode_s {
        `ifdef SV39_SUPPORTED     ignore_bins ig1 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef SV48_SUPPORTED     ignore_bins ig2 = binsof(PageType_d.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_read_u:  cross nonleaf_PTE_pbmt_d, PBMTE_set, PageType_d, lw, load_page_fault, priv_mode_u {
        `ifdef SV39_SUPPORTED     ignore_bins ig1 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef SV48_SUPPORTED     ignore_bins ig2 = binsof(PageType_d.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_write_s: cross nonleaf_PTE_pbmt_d, PBMTE_set, PageType_d, sw, store_page_fault, priv_mode_s {
        `ifdef SV39_SUPPORTED     ignore_bins ig1 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef SV48_SUPPORTED     ignore_bins ig2 = binsof(PageType_d.sv48_kilo); `endif
    }
    nonleaf_PTE_pbmt_write_u: cross nonleaf_PTE_pbmt_d, PBMTE_set, PageType_d, sw, store_page_fault, priv_mode_u {
        `ifdef SV39_SUPPORTED     ignore_bins ig1 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef SV48_SUPPORTED     ignore_bins ig2 = binsof(PageType_d.sv48_kilo); `endif
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

`ifdef H_SUPPORTED
`ifdef UDB_MXLEN_64
// Svpbmt in the VS-stage and G-stage: henvcfg.PBMTE enables PBMT in the VS-stage, and menvcfg.PBMTE in the G-stage
covergroup Svpbmt_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    csrrs : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    henvcfg : coverpoint ins.current.insn[31:20] {
        bins henvcfg = {CSR_HENVCFG};
    }
    // Each supported VS-stage mode
    vsatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            bins sv39 = {8};
        `endif
        `ifdef UDB_SV48_VSMODE_TRANSLATION
            bins sv48 = {9};
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            bins sv57 = {10};
        `endif
        `ifdef UDB_SV32_VSMODE_TRANSLATION
            bins sv32 = {1};
        `endif
    }
    // Each supported G-stage mode
    hgatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        `ifdef UDB_SV39X4_TRANSLATION
            bins sv39x4 = {8};
        `endif
        `ifdef UDB_SV48X4_TRANSLATION
            bins sv48x4 = {9};
        `endif
        `ifdef UDB_SV57X4_TRANSLATION
            bins sv57x4 = {10};
        `endif
        `ifdef UDB_SV32X4_TRANSLATION
            bins sv32x4 = {1};
        `endif
    }
    vsatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    hgatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins bare = {0};
    }
    menvcfg_pbmte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte") {
        bins off = {0};
        bins on  = {1};
    }
    henvcfg_pbmte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pbmte") {
        bins off = {0};
        bins on  = {1};
    }
    // The trap into HS-mode that the access takes, if any.  Only a trap writes scause on these instructions.
    vs_trap : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        wildcard bins none = {6'b0?????};
        bins page_fault    = {6'b101100, 6'b101101, 6'b101111};
    }
    g_trap : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        wildcard bins none    = {6'b0?????};
        bins guest_page_fault = {6'b110100, 6'b110101, 6'b110111};
    }

    // PBMT in a VS-stage leaf is reserved unless henvcfg.PBMTE = 1, and PBMT = 3 always.
    // The leaves have PBMT = 1-3, so every access with PBMTE = 0 faults.
    cp_vsatp_pbmt : cross priv_mode_vs, access, vsatp_mode, hgatp_bare, henvcfg_pbmte, vs_trap {
        ignore_bins reserved = binsof(henvcfg_pbmte.off) && binsof(vs_trap.none);
    }
    // PBMT in a G-stage leaf is reserved unless menvcfg.PBMTE = 1, and PBMT = 3 always
    cp_hgatp_pbmt : cross priv_mode_vs, access, vsatp_bare, hgatp_mode, menvcfg_pbmte, g_trap {
        ignore_bins reserved = binsof(menvcfg_pbmte.off) && binsof(g_trap.none);
    }
    // henvcfg.PBMTE is read-only zero while menvcfg.PBMTE = 0
    cp_henvcfg_menvcfg : cross priv_mode_hs, csrrs, henvcfg, menvcfg_pbmte;
endgroup
`endif // UDB_MXLEN_64
`endif // H_SUPPORTED

function void svpbmt_sample(int hart, int issue, ins_t ins);
    Svpbmt_cg.sample(ins);
    `ifdef H_SUPPORTED
        `ifdef UDB_MXLEN_64
            Svpbmt_H_cg.sample(ins);
        `endif
    `endif
endfunction
