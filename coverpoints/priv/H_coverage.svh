///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written By: Muhammad Abdullah abdullah.gohar@10xengineers.ai March 03, 2026
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_H

covergroup H_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    set_hstatus_hu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "hstatus", "hu") {
        bins hu_set = {1'b1};
    }

    hstatus_vtvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "hstatus", "vtvm") {
        bins vtvm_set = {1'b1};
        bins vtvm_unset = {1'b0};
    }

    mstatus_tvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "tvm") {
        bins tvm_set = {1'b1};
        bins tvm_unset = {1'b0};
    }

    mstatus_mpp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
        bins s_mode = {2'b01};
        bins m_mode = {2'b11};
    }

    `ifdef XLEN64
        mstatus_mpv: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv") {
            bins mpv_set = {1'b1};
            bins mpv_set = {1'b0};
        }
    `else
        mstatush_mpv: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv") {
            bins mpv_set = {1'b1};
            bins mpv_set = {1'b0};
        }
    `endif

    mstatus_mpie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpie") {
        bins mpie_set = {1'b1};
        bins mpie_unset = {1'b0};
    }

    mstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "spp") {
        bins spp_set = {1'b1};
        bins spp_unset = {1'b0};
    }

    mstatus_spie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", spie") {
        bins spie_set = {1'b1};
        bins spie_unset = {1'b0};
    }

    sstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp") {
        bins spp_set = {1'b1};
        bins spp_unset = {1'b0};
    }

    sstatus_spie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", spie") {
        bins spie_set = {1'b1};
        bins spie_unset = {1'b0};
    }

    hstatus_spv: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spv") {
        bins spv_set = {1'b1};
        bins spv_unset = {1'b0};
    }

    hstatus_vtsr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtsr") {
        bins vtsr_set = {1'b1};
        bins vtsr_unset = {1'b0};
    }

    hlv_instr: coverpoint ins.current.insn {
        wildcard bins hlv_b  = {HLV_B};
        wildcard bins hlv_bu = {HLV_BU};
        wildcard bins hlv_h  = {HLV_H};
        wildcard bins hlv_hu = {HLV_HU};
        wildcard bins hlv_w  = {HLV_W};
        `ifdef XLEN64
            wildcard bins hlv_wu = {HLV_WU};
            wildcard bins hlv_d  = {HLV_D};
        `endif
    }
    hlvx_instr: coverpoint ins.current.insn {
        wildcard bins hlvx_hu = {HLVX_HU};
        `ifdef XLEN64
            wildcard bins hlvx_wu = {HLVX_WU};
        `endif
    }
    hsv_instr: coverpoint ins.current.insn {
        wildcard bins hsv_b = {HSV_B};
        wildcard bins hsv_h = {HSV_H};
        wildcard bins hsv_w = {HSV_W};
        `ifdef XLEN64
            wildcard bins hsv_d = {HSV_D};
        `endif
    }

    hfence_instr: coverpoint ins.current.insn {
        wildcard bins hfence_vvma = {HFENCE_VVMA};
        wildcard bins hfence_gvma = {HFENCE_GVMA};
    }
    sfence_instr: coverpoint ins.current.insn {
        wildcard bins sfence_vma = {SFENCE_VMA};
    }

    mret_instr: coverpoint ins.current.insn {
        wildcard bins mret = {MRET};
    }
    sret_instr: coverpoint ins.current.insn {
        wildcard bins mret = {SRET};
    }

    g_pte_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins g_pte = {8'b????1111};
    }
    vs_pte_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins vs_pte = {8'b????1111};
    }

    cp_hlv_m:  cross priv_mode_m, vs_pte_d, g_pte_d, hlv;
    cp_hlv_hs: cross priv_mode_hs, vs_pte_d, g_pte_d, hlv;
    cp_hlv_hu: cross priv_mode_hu, set_hstatus_hu, vs_pte_d, g_pte_d, hlv_instr;

    cp_hlvx_m:  cross priv_mode_m, vs_pte_d, g_pte_d, hlvx;
    cp_hlvx_hs: cross priv_mode_hs, vs_pte_d, g_pte_d, hlvx;
    cp_hlvx_hu: cross priv_mode_hu, set_hstatus_hu, vs_pte_d, g_pte_d, hlvx_instr;

    cp_hlv_m:  cross priv_mode_m, vs_pte_d, g_pte_d, hsv;
    cp_hlv_hs: cross priv_mode_hs, vs_pte_d, g_pte_d, hsv;
    cp_hlv_hu: cross priv_mode_hu, set_hstatus_hu, vs_pte_d, g_pte_d, hsv_instr;

    cp_hfence_m:  cross priv_mode_m, mstatus_tvm, hstatus_vtvm, hfence_instr;
    cp_hfence_hs: cross priv_mode_hs, mstatus_tvm, hstatus_vtvm, hfence_instr;

    cp_sfence_m:  cross priv_mode_m, mstatus_tvm, hstatus_vtvm, sfence_instr;
    cp_sfence_hs: cross priv_mode_hs, mstatus_tvm, hstatus_vtvm, sfence_instr;
    cp_sfence_vs: cross priv_mode_vs, mstatus_tvm, hstatus_vtvm, sfence_instr;

    cp_mret_m:  cross priv_mode_m, mstatus_mpp, mstatus_mpv, mstatus_mpie, mret_instr;
    cp_sret_m:  cross priv_mode_m, mstatus_spp, mstatus_spie, hstatus_spv, sret_instr;
    cp_sret_hs: cross priv_mode_hs, sstatus_spp, sstatus_spie, hstatus_spv, sret_instr;
    cp_sret_vs: cross priv_mode_vs, sstatus_spp, sstatus_spie, hstatus_vtsr, sret_instr;

    cp_mret_illegal_hs: cross priv_mode_hs, mret_instr;
    cp_mret_illegal_vs: cross priv_mode_vs, mret_instr;
    cp_mret_illegal_vu: cross priv_mode_vu, mret_instr;
    cp_sret_illegal_vu: cross priv_mode_vu, sret_instr;

endgroup

function void vmh_sample(int hart, int issue, ins_t ins);
    H_instr_cg.sample(ins);
endfunction
