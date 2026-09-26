///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// SvHSm: two-stage address translation seen from M-mode through MPRV and MPV, and guest traps taken in M-mode.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

// The reference model trace records instructions, registers and CSRs but not PTEs, so the coverpoints record the
// access, the privilege and translation state that governs it, and the trap it takes.

`define COVER_SVHSM

covergroup SvHSm_mprv_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    load_store : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
    }
    lw : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    hlv_access : coverpoint ins.current.insn {
        wildcard bins lw    = {LW};
        wildcard bins sw    = {SW};
        wildcard bins hlv_w = {HLV_W};
        wildcard bins hsv_w = {HSV_W};
    }
    mprv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins off = {0};
        bins on  = {1};
    }
    mprv_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins on = {1};
    }
    // {MPV, MPP}: the mode whose translation MPRV = 1 selects
    `ifdef UDB_MXLEN_64
        mpp_mpv : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `else
        mpp_mpv : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `endif
        bins m  = {3'b011};
        bins hs = {3'b001};
        bins vs = {3'b101};
        bins u  = {3'b000};
        bins vu = {3'b100};
    }
    `ifdef UDB_MXLEN_64
        mpp_mpv_guest : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv")[0],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `else
        mpp_mpv_guest : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv")[0],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `endif
        bins vs = {3'b101};
        bins vu = {3'b100};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    vsatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins bare = {0};
    }
    // The trap into M-mode that the access takes, if any.  Only a trap writes mcause on these instructions.
    trap : coverpoint {ins.current.csr_wb[CSR_MCAUSE], ins.current.csr[CSR_MCAUSE][4:0]} {
        wildcard bins none = {6'b0?????};
        bins page_fault    = {6'b101101, 6'b101111};
    }
    vsstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    mstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    mstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }

    // MPRV = 1 and MPV = 1 translate M-mode loads and stores through the VS-stage
    cp_vsatp_mprv_effects : cross priv_mode_m, load_store, mprv_on, mpp_mpv_guest, vsatp_paged, hgatp_bare, trap;
    // Loads and stores use the G-stage only with MPRV = 1 and MPV = 1; HLV and HSV always do
    cp_hgatp_mprv_effects : cross priv_mode_m, hlv_access, mprv, mpp_mpv, vsatp_bare, hgatp_paged;
    // With MPV = 1, vsstatus.SUM applies instead of mstatus.SUM
    cp_mprv_sum           : cross priv_mode_m, load_store, mprv_on, mpp_mpv_guest, vsatp_paged, hgatp_paged, vsstatus_sum, mstatus_sum;
    // mstatus.MXR makes execute-only pages readable in both stages, vsstatus.MXR only in the VS-stage
    cp_mprv_mxr           : cross priv_mode_m, lw, mprv_on, mpp_mpv_guest, vsatp_paged, hgatp_paged, vsstatus_mxr, mstatus_mxr;
endgroup

covergroup SvHSm_trap_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    trap : coverpoint {ins.current.csr_wb[CSR_MCAUSE], ins.current.csr[CSR_MCAUSE][4:0]} {
        bins page_fault       = {6'b101100, 6'b101101, 6'b101111};
        bins guest_page_fault = {6'b110100, 6'b110101, 6'b110111};
    }
    // The trap records a guest virtual address and that it came from V = 1
    `ifdef UDB_MXLEN_64
        gva_mpv : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "gva")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mpv")[0]} {
    `else
        gva_mpv : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "gva")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "mpv")[0]} {
    `endif
        bins guest = {2'b11};
    }
    // The pseudoinstruction that mtinst holds after a guest-page fault on an implicit VS-stage access
    mtinst_pseudo : coverpoint ins.current.csr[CSR_MTINST] iff (ins.current.csr_wb[CSR_MTINST]) {
        `ifdef UDB_MXLEN_64
            bins read = {'h3000};
        `else
            bins read = {'h2000};
        `endif
    }

    // Guest page faults and guest-page faults taken in M-mode (mtval2 and mtinst are in the trap signature)
    cp_guest_page_fault_m : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, trap, gva_mpv;
    cp_implicit_gpf_m     : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, mtinst_pseudo;
endgroup

function void svhsm_sample(int hart, int issue, ins_t ins);
    SvHSm_mprv_cg.sample(ins);
    SvHSm_trap_cg.sample(ins);
endfunction
