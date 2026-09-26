///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// SvH: two-stage (VS-stage and G-stage) address translation in HS, VS and VU modes.
// Written By: Muhammad Abdullah abdullah.gohar@10xengineers.ai January 07, 2026
// Modified: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

// The reference model trace records instructions, registers and CSRs but not PTEs.  The coverpoints record
// each guest access with its privilege mode, the translation modes, the controls that affect it and the trap
// it takes; the PTE a testcase uses is in the test, and its effect is checked by the signature.
// TODO: once sail_to_rvvi.py records the PTEs of each walk (Sail --trace-ptw), bin the leaf's V, U, R, W, X, A, D,
// N, PBMT, RSW and reserved bits in cp_vsatp_perm, cp_hgatp_perm and cp_twostage_perm.

`define COVER_SVH

covergroup SvH_vsstage_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    lw : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins bare = {0};
    }
    // The trap into HS-mode that the access takes, if any.  Only a trap writes scause on these instructions.
    trap : coverpoint {ins.current.csr_wb[CSR_SCAUSE], ins.current.csr[CSR_SCAUSE][4:0]} {
        wildcard bins none = {6'b0?????};
        bins page_fault    = {6'b101100, 6'b101101, 6'b101111};
    }
    vsstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "")[61] {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg_pbmte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "")[62] {
            bins off = {0};
            bins on  = {1};
        }
        `ifdef SVNAPOT_SUPPORTED
            // Pages 0, 2 and 15 of the 64 KiB NAPOT region
            napot_page : coverpoint ins.current.rs1_val[15:12] {
                bins page0  = {0};
                bins page2  = {2};
                bins page15 = {15};
            }
        `endif
    `else
        menvcfg_adue : coverpoint ins.current.csr[CSR_MENVCFGH][29] {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg_adue : coverpoint ins.current.csr[CSR_HENVCFGH][29] {
            bins off = {0};
            bins on  = {1};
        }
    `endif

    // VS-stage leaf permissions and formats (hgatp = Bare), with vsstatus.SUM and vsstatus.MXR
    cp_vsatp_perm   : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_bare, trap;
    cp_vsatp_sum    : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_bare, vsstatus_sum;
    cp_vsstatus_mxr : cross priv_mode_vs_vu, lw, vsatp_paged, hgatp_bare, vsstatus_sum, vsstatus_mxr;
    // VS-stage A/D bits: Svade faults with henvcfg.ADUE = 0; Svadu updates them with henvcfg.ADUE = 1
    cp_vsatp_adue   : cross priv_mode_vs, access, vsatp_paged, hgatp_bare, menvcfg_adue, henvcfg_adue {
        // henvcfg.ADUE is read-only zero while menvcfg.ADUE = 0
        ignore_bins read_only = binsof(menvcfg_adue.off) && binsof(henvcfg_adue.on);
    }
    `ifdef UDB_MXLEN_64
        // PBMT in a VS-stage leaf is reserved unless henvcfg.PBMTE = 1, and PBMT = 3 always
        cp_vsatp_pbmt  : cross priv_mode_vs, access, vsatp_paged, hgatp_bare, henvcfg_pbmte, trap;
        `ifdef SVNAPOT_SUPPORTED
            cp_vsatp_napot : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_bare, napot_page;
        `endif
    `endif
endgroup

covergroup SvH_gstage_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    lw : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    vsatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    trap : coverpoint {ins.current.csr_wb[CSR_SCAUSE], ins.current.csr[CSR_SCAUSE][4:0]} {
        wildcard bins none     = {6'b0?????};
        bins guest_page_fault  = {6'b110100, 6'b110101, 6'b110111};
    }
    // HS-level MXR: mret into the guest logs mstatus
    mstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            bins on  = {1};
        }
        menvcfg_pbmte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte") {
            bins off = {0};
            bins on  = {1};
        }
        `ifdef SVNAPOT_SUPPORTED
            napot_page : coverpoint ins.current.rs1_val[15:12] {
                bins page0  = {0};
                bins page2  = {2};
                bins page15 = {15};
            }
        `endif
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
        }
        // The one set bit above bit 36 of the guest physical address (vsatp = Bare)
        gpa_bit : coverpoint ($clog2(ins.current.rs1_val + 1) - 1) {
            bins b[] = {[37:63]};
        }
    `else
        menvcfg_adue : coverpoint ins.current.csr[CSR_MENVCFGH][29] {
            bins off = {0};
            bins on  = {1};
        }
    `endif

    // G-stage leaf permissions and formats (vsatp = Bare); the U bit is checked as for U-mode
    cp_hgatp_perm : cross priv_mode_vs_vu, access, vsatp_bare, hgatp_paged, trap;
    // Only the HS-level MXR makes G-stage execute-only pages readable
    cp_hgatp_mxr  : cross priv_mode_vs_vu, lw, vsatp_bare, hgatp_paged, mstatus_mxr, vsstatus_mxr;
    // G-stage A/D bits: Svade faults with menvcfg.ADUE = 0; Svadu updates them with menvcfg.ADUE = 1
    cp_hgatp_adue : cross priv_mode_vs, access, vsatp_bare, hgatp_paged, menvcfg_adue;
    `ifdef UDB_MXLEN_64
        cp_hgatp_pbmt  : cross priv_mode_vs, access, vsatp_bare, hgatp_paged, menvcfg_pbmte, trap;
        `ifdef SVNAPOT_SUPPORTED
            cp_hgatp_napot : cross priv_mode_vs_vu, access, vsatp_bare, hgatp_paged, napot_page;
        `endif
        // Guest physical address bits above the mode's width raise guest-page faults
        cp_hgatp_gpa_width : cross priv_mode_vs, lw, vsatp_bare, hgatp_mode, gpa_bit {
            `ifdef UDB_SV48X4_TRANSLATION
                ignore_bins sv48x4_below_root = binsof(hgatp_mode.sv48x4) && binsof(gpa_bit) intersect {[37:38]};
            `endif
            `ifdef UDB_SV57X4_TRANSLATION
                ignore_bins sv57x4_below_root = binsof(hgatp_mode.sv57x4) && binsof(gpa_bit) intersect {[37:47]};
            `endif
        }
    `endif
endgroup

covergroup SvH_twostage_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    lw : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    jalr : coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    vsatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    hgatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins bare = {0};
    }
    trap : coverpoint {ins.current.csr_wb[CSR_SCAUSE], ins.current.csr[CSR_SCAUSE][4:0]} {
        wildcard bins none     = {6'b0?????};
        bins page_fault        = {6'b101100, 6'b101101, 6'b101111};
        bins guest_page_fault  = {6'b110100, 6'b110101, 6'b110111};
    }
    guest_page_fault : coverpoint {ins.current.csr_wb[CSR_SCAUSE], ins.current.csr[CSR_SCAUSE][4:0]} {
        bins guest_page_fault  = {6'b110100, 6'b110101, 6'b110111};
    }
    // A page fault delegated to VS-mode
    vs_page_fault : coverpoint {ins.current.csr_wb[CSR_VSCAUSE], ins.current.csr[CSR_VSCAUSE][4:0]} {
        bins page_fault = {6'b101100, 6'b101101, 6'b101111};
    }
    hedeleg_page_faults : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[15:12] {
        bins delegated = {4'b1011};
    }
    mstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    // The pseudoinstruction that htinst holds after a guest-page fault on an implicit VS-stage access
    htinst_pseudo : coverpoint ins.current.csr[CSR_HTINST] iff (ins.current.csr_wb[CSR_HTINST]) {
        `ifdef UDB_MXLEN_64
            bins read  = {'h3000};
            bins write = {'h3020};
        `else
            bins read  = {'h2000};
            bins write = {'h2020};
        `endif
    }
    // A fetch at the last halfword of a page
    page_end : coverpoint ins.current.rs1_val[11:0] {
        bins page_end = {12'hffe};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "")[61] {
            bins off = {0};
            bins on  = {1};
        }
        `ifdef SVNAPOT_SUPPORTED
            napot_page : coverpoint ins.current.rs1_val[15:12] {
                bins page0  = {0};
                bins page2  = {2};
                bins page15 = {15};
            }
        `endif
    `else
        menvcfg_adue : coverpoint ins.current.csr[CSR_MENVCFGH][29] {
            bins off = {0};
            bins on  = {1};
        }
        henvcfg_adue : coverpoint ins.current.csr[CSR_HENVCFGH][29] {
            bins off = {0};
            bins on  = {1};
        }
        // Guest physical address bits 33:32, which htval reports as bits 31:30 after a guest-page fault
        htval_gpa_high : coverpoint ins.current.csr[CSR_HTVAL][31:30] iff (ins.current.csr_wb[CSR_HTVAL]) {
            bins bit32 = {1};
            bins bit33 = {2};
            bins both  = {3};
        }
    `endif

    // VS-stage and G-stage permissions combined: a VS-stage denial is a page fault, a G-stage one a guest-page fault
    cp_twostage_perm   : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, trap;
    // vsstatus.MXR affects only the VS-stage; the HS-level MXR affects both
    cp_twostage_mxr    : cross priv_mode_vs_vu, lw, vsatp_paged, hgatp_paged, vsstatus_mxr, mstatus_mxr;
    cp_twostage_adue   : cross priv_mode_vs, access, vsatp_paged, hgatp_paged, menvcfg_adue, henvcfg_adue {
        ignore_bins read_only = binsof(menvcfg_adue.off) && binsof(henvcfg_adue.on);
    }
    // Guest-page faults on implicit VS-stage page-table reads and A/D writes
    cp_implicit_gpf    : cross priv_mode_vs, access, vsatp_paged, hgatp_paged, htinst_pseudo;
    // Page faults go to VS-mode when hedeleg delegates them; guest-page faults cannot be delegated
    cp_hedeleg_page_fault       : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, hedeleg_page_faults, vs_page_fault;
    cp_hedeleg_guest_page_fault : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, hedeleg_page_faults, guest_page_fault;
    cp_stage_both_bare : cross priv_mode_vs_vu, access, vsatp_bare, hgatp_bare;
    `ifdef ZCA_SUPPORTED
        // A fetch straddling a page boundary faults on the second page
        cp_straddle    : cross priv_mode_vs, jalr, vsatp_paged, hgatp_paged, page_end, trap;
    `endif
    `ifdef UDB_MXLEN_64
        `ifdef SVNAPOT_SUPPORTED
            cp_twostage_napot   : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, napot_page;
        `endif
    `else
        // Sv32x4 translates 34-bit guest physical addresses
        cp_hgatp_sv32x4_gpa : cross priv_mode_vs, lw, vsatp_paged, hgatp_paged, htval_gpa_high;
    `endif
endgroup

covergroup SvH_hlv_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    hlv : coverpoint ins.current.insn {
        wildcard bins hlv_w   = {HLV_W};
        wildcard bins hlvx_wu = {HLVX_WU};
        wildcard bins hsv_w   = {HSV_W};
    }
    hlv_load : coverpoint ins.current.insn {
        wildcard bins hlv_w   = {HLV_W};
        wildcard bins hlvx_wu = {HLVX_WU};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    hstatus_spvp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        bins vu = {0};
        bins vs = {1};
    }
    vsstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    sstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    sstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }

    // hstatus.SPVP selects VU-level or VS-level access; vsstatus.SUM applies and sstatus.SUM does not
    cp_hlv_priv : cross priv_mode_hs, hlv, vsatp_paged, hgatp_paged, hstatus_spvp, vsstatus_sum, sstatus_sum;
    // sstatus.MXR affects both stages, vsstatus.MXR only the VS-stage
    cp_hlv_mxr  : cross priv_mode_hs, hlv_load, vsatp_paged, hgatp_paged, vsstatus_mxr, sstatus_mxr;
endgroup

covergroup SvH_csr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    csrrs : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    henvcfg : coverpoint ins.current.insn[31:20] {
        `ifdef UDB_MXLEN_64
            bins henvcfg = {CSR_HENVCFG};
        `else
            bins henvcfgh = {CSR_HENVCFGH};
        `endif
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            bins on  = {1};
        }
        vsatp : coverpoint ins.current.insn[31:20] {
            bins vsatp = {CSR_VSATP};
        }
        hgatp : coverpoint ins.current.insn[31:20] {
            bins hgatp = {CSR_HGATP};
        }
        satp : coverpoint ins.current.insn[31:20] {
            bins satp = {CSR_SATP};
        }
        mode_written : coverpoint ins.current.rs1_val[63:60] {
            bins b[] = {[0:15]};
        }
        vsatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins bare = {0};
            bins sv39 = {8};
        }
        hgatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
            bins bare   = {0};
            bins sv39x4 = {8};
        }
        // In VS-mode, satp is vsatp
        satp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
            bins bare = {0};
            bins sv39 = {8};
        }

        // Each MODE written starting from Bare and Sv39 (Sv39x4)
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            cp_vsatp_mode_field : cross priv_mode_hs, csrrw, vsatp, vsatp_mode, mode_written;
            cp_satp_mode_field  : cross priv_mode_vs, csrrw, satp, satp_mode, mode_written;
        `endif
        `ifdef UDB_SV39X4_TRANSLATION
            cp_hgatp_mode_field : cross priv_mode_hs, csrrw, hgatp, hgatp_mode, mode_written;
        `endif
    `else
        menvcfg_adue : coverpoint ins.current.csr[CSR_MENVCFGH][29] {
            bins off = {0};
            bins on  = {1};
        }
    `endif

    // henvcfg.ADUE and PBMTE are read-only zero while the menvcfg bits are zero
    cp_henvcfg_menvcfg : cross priv_mode_hs, csrrs, henvcfg, menvcfg_adue;
endgroup

function void svh_sample(int hart, int issue, ins_t ins);
    SvH_vsstage_cg.sample(ins);
    SvH_gstage_cg.sample(ins);
    SvH_twostage_cg.sample(ins);
    SvH_hlv_cg.sample(ins);
    SvH_csr_cg.sample(ins);
endfunction
