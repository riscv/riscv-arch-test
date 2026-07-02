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

`define COVER_SSSTRICTU
covergroup SsstrictU_ucsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }
    csrr: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    // Similar to SsstrictSm/S, but exercises all user CSRs except user custom. Insufficient permission CSRs tested in U_coverage.
    csr: coverpoint ins.current.insn[31:20]  {
        bins user_std0[] = {[12'h000:12'h0FF]};
        ignore_bins super_std0[] = {[12'h100:12'h17F]};
        ignore_bins super_std02[] = {[12'h180:12'h1FF]};
        ignore_bins hyper_std0[] = {[12'h200:12'h2FF]};
        ignore_bins mach_std0[] = {[12'h300:12'h3FF]};
        bins user_std1[] = {[12'h400:12'h4FF]};
        ignore_bins super_std1[] = {[12'h500:12'h5BF]};
        ignore_bins super_custom1 = {[12'h5C0:12'h5FF]};
        ignore_bins hyper_std1[] = {[12'h600:12'h6BF]};
        ignore_bins hyper_custom1 = {[12'h6C0:12'h6FF]};
        ignore_bins mach_std1[] = {[12'h700:12'h7AF]};
        ignore_bins mach_debug[] = {[12'h7A0:12'h7AF]};
        ignore_bins debug_only[] = {[12'h7B0:12'h7BF]};
        ignore_bins mach_custom1[] = {[12'h7C0:12'h7FF]};
        ignore_bins user_custom2 = {[12'h800:12'h8FF]};
        ignore_bins super_std2[] = {[12'h900:12'h9BF]};
        ignore_bins super_custom22 = {[12'h9C0:12'h9FF]};
        ignore_bins hyper_std2[] = {[12'hA00:12'hABF]};
        ignore_bins hyper_custom22 = {[12'hAC0:12'hAFF]};
        ignore_bins mach_std2[] = {[12'hB00:12'hBBF]};
        ignore_bins mach_custom2[] = {[12'hBC0:12'hBFF]};
        bins user_std3[] = {[12'hC00:12'hCBF]};
        ignore_bins user_custom3 = {[12'hCC0:12'hCFF]};
        ignore_bins super_std3[] = {[12'hD00:12'hDBF]};
        ignore_bins super_custom3 = {[12'hDC0:12'hDFF]};
        ignore_bins hyper_std3[] = {[12'hE00:12'hEBF]};
        ignore_bins hyper_custom3 = {[12'hEC0:12'hEFF]};
        ignore_bins mach_std3[] = {[12'hF00:12'hFBF]};
        ignore_bins mach_custom3[] = {[12'hFC0:12'hFFF]};
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

    // main coverpoints
    cp_csrr:       cross csrr,  csr,   priv_mode_u, nonzerord;
    cp_csrw_edges: cross csrrw, csr,   priv_mode_u, rs1_edges;
    cp_csrcs:      cross csrop, csr,   priv_mode_u, rs1_ones;
endgroup

covergroup SsstrictU_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_instr.svh"
    `include "priv/RISCV_coverage_vect_instr.svh"

    // main coverpoints
    cp_illegal:           cross priv_mode_u, illegal;
    cp_load:              cross priv_mode_u, load;
    cp_fload:             cross priv_mode_u, fload;
    cp_fence_cbo:         cross priv_mode_u, fence_cbo;
    cp_cbo_immediate:     cross priv_mode_u, cbo_immediate;
    cp_cbo_rd:            cross priv_mode_u, cbo_rd;
    cp_Itype:             cross priv_mode_u, Itype;
    cp_Itypef3:           cross priv_mode_u, Itypef3;
    cp_aes64ks1i:         cross priv_mode_u, aes64ks1i;
    cp_IWtype:            cross priv_mode_u, IWtype;
    cp_IWshift:           cross priv_mode_u, IWshift;
    cp_store:             cross priv_mode_u, store;
    cp_fstore:            cross priv_mode_u, fstore;
    cp_atomic_funct3:     cross priv_mode_u, atomic_funct3;
    cp_atomic_funct7:     cross priv_mode_u, atomic_funct7;
    cl_lrsc:              cross priv_mode_u, lrsc;
    cp_Rtype:             cross priv_mode_u, Rtype;
    cp_RWtype:            cross priv_mode_u, RWtype;
    cp_Ftype:             cross priv_mode_u, Ftype;
    cp_fsqrt:             cross priv_mode_u, fsqrt;
    cp_fclass:            cross priv_mode_u, fclass;
    cp_fcvtif:            cross priv_mode_u, fcvtif;
    cp_fcvtif_fmt:        cross priv_mode_u, fcvtif_fmt;
    cp_fcvtfi:            cross priv_mode_u, fcvtfi;
    cp_fcvtfi_fmt:        cross priv_mode_u, fcvtfi_fmt;
    cp_fcvtff:            cross priv_mode_u, fcvtff;
    cp_fcvtff_fmt:        cross priv_mode_u, fcvtff_fmt;
    cp_fmvif:             cross priv_mode_u, fmvif;
    cp_fmvfi:             cross priv_mode_u, fmvfi;
    cp_fli:               cross priv_mode_u, fli;
    cp_fmvh:              cross priv_mode_u, fmvh;
    cp_fmvp:              cross priv_mode_u, fmvp;
    cp_cvtmodwd:          cross priv_mode_u, cvtmodwd;
    cp_cvtmodwdfrm:       cross priv_mode_u, cvtmodwdfrm;
    cp_branch:            cross priv_mode_u, branch;
    cp_jalr:              cross priv_mode_u, jalr;
    cp_privileged_funct3: cross priv_mode_u, privileged_funct3;
    cp_privileged_000:    cross priv_mode_u, privileged_000;
    cp_privileged_rd:     cross priv_mode_u, privileged_rd;
    cp_privileged_rs2:    cross priv_mode_u, privileged_rs2;
    cp_reserved:          cross priv_mode_u, reserved;
    cp_upperreg_rs1:      cross priv_mode_u, upperreg_rs1;
    cp_upperreg_rs2:      cross priv_mode_u, upperreg_rs2;
    cp_upperreg_rd:       cross priv_mode_u, upperreg_rd;
    cp_upperreg_imm_rd:   cross priv_mode_u, upperreg_imm_rd;
    cp_upperreg_imm_rs1:  cross priv_mode_u, upperreg_imm_rs1;
    cp_upperreg_fmv_rs1 : cross priv_mode_u, upperreg_fmv_rs1;
    cp_upperreg_fmv_rd :  cross priv_mode_u, upperreg_fmv_rd;
    cp_amocas_odd :       cross priv_mode_u, amocas_odd;

    // ── Vector coverpoints crossed with priv_mode_u ──────────────────
    // Definitions are in RISCV_coverage_vect_instr.svh; only the cross
    // with privilege mode belongs here.

    // vset* reserved encodings
    cp_v_vsetvl:          cross priv_mode_u, v_vsetvl;
    cp_v_vsetvli_sew:     cross priv_mode_u, v_vsetvli_sew;
    cp_v_vsetvli_res:     cross priv_mode_u, v_vsetvli_res;
    cp_v_vsetivli_sew:    cross priv_mode_u, v_vsetivli_sew;
    cp_v_vsetivli_res:    cross priv_mode_u, v_vsetivli_res;

    // Vector load/store reserved encodings
    cp_vl_width:          cross priv_mode_u, vl_width;
    cp_vl_lumop:          cross priv_mode_u, vl_lumop;
    cp_vs_width:          cross priv_mode_u, vs_width;
    cp_vs_sumop:          cross priv_mode_u, vs_sumop;

    // Vector arithmetic funct6 × SEW
    cp_v_IVV_f6:          cross priv_mode_u, v_IVV_f6, current_vsew;
    cp_v_FVV_f6:          cross priv_mode_u, v_FVV_f6, current_vsew;
    cp_v_MVV_f6:          cross priv_mode_u, v_MVV_f6, current_vsew;
    cp_v_IVI_f6:          cross priv_mode_u, v_IVI_f6, current_vsew;
    cp_v_IVX_f6:          cross priv_mode_u, v_IVX_f6, current_vsew;
    cp_v_FVF_f6:          cross priv_mode_u, v_FVF_f6, current_vsew;
    cp_v_MVX_f6:          cross priv_mode_u, v_MVX_f6, current_vsew;

    // Vector unary instructions
    cp_v_VWRXUNARY0:      cross priv_mode_u, v_VWRXUNARY0, current_vsew;
    cp_v_VRXUNARY0:       cross priv_mode_u, v_VRXUNARY0, current_vsew;
    cp_v_VXUNARY0:        cross priv_mode_u, v_VXUNARY0, current_vsew;
    cp_v_VMUNARY0:        cross priv_mode_u, v_VMUNARY0, current_vsew;
    cp_v_VWFUNARY0:       cross priv_mode_u, v_VWFUNARY0, current_vsew;
    cp_v_VRFUNARY0:       cross priv_mode_u, v_VRFUNARY0, current_vsew;
    cp_v_VFUNARY0:        cross priv_mode_u, v_VFUNARY0, current_vsew;
    cp_v_VFUNARY1:        cross priv_mode_u, v_VFUNARY1, current_vsew;

    // Vector crypto
    cp_vopve:             cross priv_mode_u, v_vopve, current_vsew;
    cp_v_vaesvv:          cross priv_mode_u, v_vaesvv, current_vsew;
    cp_v_vaesvs:          cross priv_mode_u, v_vaesvs, current_vsew;

endgroup

covergroup SsstrictU_comp_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_comp_instr.svh"

    // main coverpoints
    cp_compressed00: cross priv_mode_u, compressed00;
    cp_compressed01: cross priv_mode_u, compressed01;
    cp_compressed10: cross priv_mode_u, compressed10;
endgroup


function void ssstrictu_sample(int hart, int issue, ins_t ins);
    SsstrictU_ucsr_cg.sample(ins);
    SsstrictU_instr_cg.sample(ins);
    SsstrictU_comp_instr_cg.sample(ins);
endfunction
