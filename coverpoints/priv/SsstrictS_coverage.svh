///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 23 March 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSSTRICTS
covergroup SsstrictS_scsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }
    csrr: coverpoint ins.current.insn  {
        wildcard bins csrr = {32'b????????????_00000_010_?????_1110011};
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b????????????_?????_001_?????_1110011};
    }
    // csr is similar to in ZicsrM, but also exercises custom/debug machine mode CSRs, which should trap from supervisor level
    csr: coverpoint ins.current.insn[31:20]  {
        bins user_std0[] = {[12'h000:12'h0FF]};
        bins super_std0[] = {[12'h100:12'h17F]};
        bins super_std02[] = {[12'h181:12'h1FF]};
        bins hyper_std0[] = {[12'h200:12'h2FF]};
        bins mach_std0[] = {[12'h300:12'h3FF]};
        bins user_std1[] = {[12'h400:12'h4FF]};
        bins super_std1[] = {[12'h500:12'h5BF]};
        ignore_bins super_custom1 = {[12'h5C0:12'h5FF]};
        bins hyper_std1[] = {[12'h600:12'h6BF]};
        ignore_bins hyper_custom1 = {[12'h6C0:12'h6FF]};
        bins mach_std1[] = {[12'h700:12'h7AF]};
        bins mach_debug[] = {[12'h7A0:12'h7AF]}; // toggling debug registers could do weird stuff
        bins debug_only[] = {[12'h7B0:12'h7BF]}; // access to debug mode registers raises illegal instruction even in machine mode
        bins mach_custom1[] = {[12'h7C0:12'h7FF]};
        ignore_bins user_custom2 = {[12'h800:12'h8FF]};
        bins super_std2[] = {[12'h900:12'h9BF]};
        ignore_bins super_custom22 = {[12'h9C0:12'h9FF]};
        bins hyper_std2[] = {[12'hA00:12'hABF]};
        ignore_bins hyper_custom22 = {[12'hAC0:12'hAFF]};
        bins mach_std2[] = {[12'hB00:12'hBBF]};
        bins mach_custom2[] = {[12'hBC0:12'hBFF]};
        bins user_std3[] = {[12'hC00:12'hCBF]};
        ignore_bins user_custom3 = {[12'hCC0:12'hCFF]};
        bins super_std3[] = {[12'hD00:12'hDBF]};
        ignore_bins super_custom3 = {[12'hDC0:12'hDFF]};
        bins hyper_std3[] = {[12'hE00:12'hEBF]};
        ignore_bins hyper_custom3 = {[12'hEC0:12'hEFF]};
        bins mach_std3[] = {[12'hF00:12'hFBF]};
        bins mach_custom3[] = {[12'hFC0:12'hFFF]};
    }
    rs1_ones: coverpoint ins.current.rs1_val {
        bins ones = {'1};
    }
    rs1_edges: coverpoint ins.current.rs1_val {
        bins zero = {0};
        bins ones = {'1};
    }
    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }
    mcsrs: coverpoint ins.current.insn[31:20] {
        bins mstatus = {12'h300};
        bins mie     = {12'h304};
        bins mip     = {12'h344};
    }
    scsrs: coverpoint ins.current.insn[31:20] {
        bins sstatus = {12'h100};
        bins sie     = {12'h104};
        bins sip     = {12'h144};
    }

    // main coverpoints
    cp_csrr:         cross csrr,    csr,         priv_mode_s, nonzerord;
    cp_csrw_edges: cross csrrw,   csr, priv_mode_s, rs1_edges {
    }

    cp_csrcs:        cross csrop,   csr, priv_mode_s, rs1_ones {
    }
    cp_shadow_m:     cross csrrw,   mcsrs,       priv_mode_m, rs1_edges;  // write 1s/0s to mstatus, mie, mip in m mode
    cp_shadow_s:     cross csrrw,   scsrs,       priv_mode_s, rs1_edges;  // write 1s/0s to sstatus, sie, sip in s mode
endgroup

covergroup SsstrictS_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_instr.svh"

    // main coverpoints
    cp_illegal:           cross priv_mode_s, illegal;
    cp_load:              cross priv_mode_s, load;
    cp_fload:             cross priv_mode_s, fload;
    cp_fence_cbo:         cross priv_mode_s, fence_cbo;
    cp_cbo_immediate:     cross priv_mode_s, cbo_immediate;
    cp_cbo_rd:            cross priv_mode_s, cbo_rd;
    cp_Itype:             cross priv_mode_s, Itype;
    cp_Itypef3:           cross priv_mode_s, Itypef3;
    cp_aes64ks1i:         cross priv_mode_s, aes64ks1i;
    cp_IWtype:            cross priv_mode_s, IWtype;
    cp_IWshift:           cross priv_mode_s, IWshift;
    cp_store:             cross priv_mode_s, store;
    cp_fstore:            cross priv_mode_s, fstore;
    cp_atomic_funct3:     cross priv_mode_s, atomic_funct3;
    cp_atomic_funct7:     cross priv_mode_s, atomic_funct7;
    cl_lrsc:              cross priv_mode_s, lrsc;
    cp_Rtype:             cross priv_mode_s, Rtype;
    cp_RWtype:            cross priv_mode_s, RWtype;
    cp_Ftype:             cross priv_mode_s, Ftype;
    cp_fsqrt:             cross priv_mode_s, fsqrt;
    cp_fclass:            cross priv_mode_s, fclass;
    cp_fcvtif:            cross priv_mode_s, fcvtif;
    cp_fcvtif_fmt:        cross priv_mode_s, fcvtif_fmt;
    cp_fcvtfi:            cross priv_mode_s, fcvtfi;
    cp_fcvtfi_fmt:        cross priv_mode_s, fcvtfi_fmt;
    cp_fcvtff:            cross priv_mode_s, fcvtff;
    cp_fcvtff_fmt:        cross priv_mode_s, fcvtff_fmt;
    cp_fmvif:             cross priv_mode_s, fmvif;
    cp_fmvfi:             cross priv_mode_s, fmvfi;
    cp_fli:               cross priv_mode_s, fli;
    cp_fmvh:              cross priv_mode_s, fmvh;
    cp_fmvp:              cross priv_mode_s, fmvp;
    cp_cvtmodwd:          cross priv_mode_s, cvtmodwd;
    cp_branch:            cross priv_mode_s, branch;
    cp_jalr:              cross priv_mode_s, jalr;
    cp_privileged_funct3: cross priv_mode_s, privileged_funct3;
    cp_privileged_000:    cross priv_mode_s, privileged_000;
    cp_privileged_rd:     cross priv_mode_s, privileged_rd;
    cp_privileged_rs2:    cross priv_mode_s, privileged_rs2;
    cp_reserved:          cross priv_mode_s, reserved;
endgroup

covergroup SsstrictS_comp_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_comp_instr.svh"

    // main coverpoints
    cp_compressed00: cross priv_mode_s, compressed00;
    cp_compressed01: cross priv_mode_s, compressed01;
    cp_compressed10: cross priv_mode_s, compressed10;
endgroup


function void ssstricts_sample(int hart, int issue, ins_t ins);
    SsstrictS_scsr_cg.sample(ins);
    SsstrictS_instr_cg.sample(ins);
    SsstrictS_comp_instr_cg.sample(ins);
endfunction
