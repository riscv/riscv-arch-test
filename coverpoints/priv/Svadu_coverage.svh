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

    // A CBO sets A.  cbo.zero also sets D, because it writes; a cache-block management instruction never checks or
    // sets D (cmo.adoc).  The tests read each leaf back.  The tests run at every level, but the crosses leave out
    // PageType_d, which Sail's trace reports as a kilopage for every access.
    `ifdef ZICBOM_SUPPORTED
        cbm: coverpoint ins.current.insn {
            wildcard bins clean = {CBO_CLEAN};
            wildcard bins flush = {CBO_FLUSH};
            wildcard bins inval = {CBO_INVAL};
        }
        Abit_unset_cbm_s: cross PTE_Abit_unset_s_d, Svadu_enabled, cbm, priv_mode_s;
        Dbit_unset_cbm_s: cross PTE_Dbit_unset_s_d, Svadu_enabled, cbm, priv_mode_s;
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cbz: coverpoint ins.current.insn {
            wildcard bins zero = {CBO_ZERO};
        }
        Abit_unset_cbz_s: cross PTE_Abit_unset_s_d, Svadu_enabled, cbz, priv_mode_s;
        Dbit_unset_cbz_s: cross PTE_Dbit_unset_s_d, Svadu_enabled, cbz, priv_mode_s;
    `endif

endgroup

`ifdef H_SUPPORTED
// Svadu in the VS-stage and G-stage: menvcfg.ADUE selects Svade or Svadu for the G-stage, and henvcfg.ADUE for the
// VS-stage.  The ADUE = 0 crosses repeat Sv_H_cg's Svade crosses.
covergroup Svadu_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    hlv : coverpoint ins.current.insn {
        wildcard bins hlv_w   = {HLV_W};
        wildcard bins hlvx_wu = {HLVX_WU};
        wildcard bins hsv_w   = {HSV_W};
    }
    csrrs : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
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
    // Each pair of VS-stage and G-stage modes with the same number of levels that the hart supports
    stage_modes : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[3:0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")[3:0]} {
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            `ifdef UDB_SV39X4_TRANSLATION
                bins sv39_sv39x4 = {8'h88};
            `endif
        `endif
        `ifdef UDB_SV48_VSMODE_TRANSLATION
            `ifdef UDB_SV48X4_TRANSLATION
                bins sv48_sv48x4 = {8'h99};
            `endif
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            `ifdef UDB_SV57X4_TRANSLATION
                bins sv57_sv57x4 = {8'haa};
            `endif
        `endif
        `ifdef UDB_SV32_VSMODE_TRANSLATION
            `ifdef UDB_SV32X4_TRANSLATION
                bins sv32_sv32x4 = {8'h11};
            `endif
        `endif
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "adue") {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg : coverpoint ins.current.insn[31:20] {
            bins henvcfg = {CSR_HENVCFG};
        }
        // The write pseudoinstruction that htinst holds after a guest-page fault on a VS-stage A/D update
        htinst_write : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htinst", "htinst") iff (ins.current.csr_wb[CSR_HTINST]) {
            bins write = {'h3020};
        }
    `else
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "adue") {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "adue") {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg : coverpoint ins.current.insn[31:20] {
            bins henvcfgh = {CSR_HENVCFGH};
        }
        htinst_write : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htinst", "htinst") iff (ins.current.csr_wb[CSR_HTINST]) {
            bins write = {'h2020};
        }
    `endif

    // VS-stage A/D bits (hgatp = Bare): Svade faults with henvcfg.ADUE = 0; Svadu updates them with henvcfg.ADUE = 1
    cp_vsatp_adue    : cross priv_mode_vs, access, vsatp_mode, hgatp_bare, menvcfg_adue, henvcfg_adue {
        // henvcfg.ADUE is read-only zero while menvcfg.ADUE = 0
        ignore_bins read_only = binsof(menvcfg_adue.off) && binsof(henvcfg_adue.on);
    }
    // G-stage A/D bits (vsatp = Bare): Svade faults with menvcfg.ADUE = 0; Svadu updates them with menvcfg.ADUE = 1
    cp_hgatp_adue    : cross priv_mode_vs, access, vsatp_bare, hgatp_mode, menvcfg_adue;
    cp_twostage_adue : cross priv_mode_vs, access, stage_modes, menvcfg_adue, henvcfg_adue {
        ignore_bins read_only = binsof(menvcfg_adue.off) && binsof(henvcfg_adue.on);
    }
    // A guest-page fault on the implicit store that updates a VS-stage A or D bit
    cp_implicit_gpf  : cross priv_mode_vs, access, stage_modes, htinst_write;
    cp_hlv_implicit  : cross priv_mode_hs, hlv, stage_modes, htinst_write;
    // henvcfg.ADUE is read-only zero while menvcfg.ADUE = 0
    cp_henvcfg_menvcfg : cross priv_mode_hs, csrrs, henvcfg, menvcfg_adue;

    // CBOs with ADUE = 1 through leaves with A = D = 0: A is set in each stage, and D too for cbo.zero; a
    // cache-block management instruction never checks or sets D (cmo.adoc).  The tests read each leaf back.
    `ifdef CBO_SUPPORTED
        cbo : coverpoint ins.current.insn {
            `ifdef ZICBOM_SUPPORTED
                wildcard bins clean = {CBO_CLEAN};
                wildcard bins flush = {CBO_FLUSH};
                wildcard bins inval = {CBO_INVAL};
            `endif
            `ifdef ZICBOZ_SUPPORTED
                wildcard bins zero = {CBO_ZERO};
            `endif
        }
        vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins paged = {[1:15]};
        }
        hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
            bins paged = {[1:15]};
        }
        `ifdef UDB_MXLEN_64
            menvcfg_adue_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
                bins on = {1};
            }
            henvcfg_adue_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "adue") {
                bins on = {1};
            }
        `else
            menvcfg_adue_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "adue") {
                bins on = {1};
            }
            henvcfg_adue_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "adue") {
                bins on = {1};
            }
        `endif
        cp_vsatp_adue_cbo : cross priv_mode_vs, cbo, vsatp_paged, hgatp_bare, menvcfg_adue_on, henvcfg_adue_on;
        cp_hgatp_adue_cbo : cross priv_mode_vs, cbo, vsatp_bare, hgatp_paged, menvcfg_adue_on;
    `endif
endgroup
`endif // H_SUPPORTED

function void svadu_sample(int hart, int issue, ins_t ins);
    Svadu_cg.sample(ins);
    `ifdef H_SUPPORTED
        Svadu_H_cg.sample(ins);
    `endif
endfunction
