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

`define COVER_SSSTRICTSM

covergroup SsstrictSm_mcsr_cg with function sample(ins_t ins);
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
    csr: coverpoint ins.current.insn[31:20]  {
        bins user_std0[] = {[12'h000:12'h0FF]};
        bins super_std0[] = {[12'h100:12'h1FF]};
        bins hyper_std0[] = {[12'h200:12'h2FF]};
        bins mach_std0[] = {[12'h300:12'h3FF]};
        ignore_bins PMP_regs = {[12'h3A0:12'h3EF]};
        bins user_std1[] = {[12'h400:12'h4FF]};
        bins super_std1[] = {[12'h500:12'h5BF]};
        ignore_bins super_custom1 = {[12'h5C0:12'h5FF]};
        bins hyper_std1[] = {[12'h600:12'h6BF]};
        ignore_bins hyper_custom1 = {[12'h6C0:12'h6FF]};
        bins mach_std1[] = {[12'h700:12'h7AF]};
        ignore_bins mach_debug = {[12'h7A0:12'h7AF]};
        bins debug_only[] = {[12'h7B0:12'h7BF]};
        ignore_bins mach_custom1 = {[12'h7C0:12'h7FF]};
        ignore_bins user_custom2 = {[12'h800:12'h8FF]};
        bins super_std2[] = {[12'h900:12'h9BF]};
        ignore_bins super_custom22 = {[12'h9C0:12'h9FF]};
        bins hyper_std2[] = {[12'hA00:12'hABF]};
        ignore_bins hyper_custom22 = {[12'hAC0:12'hAFF]};
        bins mach_std2[] = {[12'hB00:12'hBBF]};
        ignore_bins mach_custom2 = {[12'hBC0:12'hBFF]};
        bins user_std3[] = {[12'hC00:12'hCBF]};
        ignore_bins user_custom3 = {[12'hCC0:12'hCFF]};
        bins super_std3[] = {[12'hD00:12'hDBF]};
        ignore_bins super_custom3 = {[12'hDC0:12'hDFF]};
        bins hyper_std3[] = {[12'hE00:12'hEBF]};
        ignore_bins hyper_custom3 = {[12'hEC0:12'hEFF]};
        ignore_bins mach_std3_readonly = {[12'hF00:12'hFBF]}; // Read-only M-mode CSRs, not testable
        ignore_bins mach_custom3 = {[12'hFC0:12'hFFF]};
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
    cp_csrr:         cross priv_mode_m, csrr,     csr,   nonzerord;
    cp_csrw_edges:   cross priv_mode_m, csrrw,    csr,   rs1_edges;
    cp_csrcs:        cross priv_mode_m, csrop,    csr,   rs1_ones;
endgroup


covergroup SsstrictSm_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/RISCV_coverage_instr.svh"
    `include "priv/RISCV_coverage_vect_instr.svh"

    // ── Scalar illegal instruction coverpoints ───────────────────────

    cp_illegal:           cross priv_mode_m, illegal;
    cp_load:              cross priv_mode_m, load;
    cp_fload:             cross priv_mode_m, fload;
    cp_fence_cbo:         cross priv_mode_m, fence_cbo;
    cp_cbo_immediate:     cross priv_mode_m, cbo_immediate;
    cp_cbo_rd:            cross priv_mode_m, cbo_rd;
    cp_Itype:             cross priv_mode_m, Itype;
    cp_Itypef3:           cross priv_mode_m, Itypef3;
    cp_aes64ks1i:         cross priv_mode_m, aes64ks1i;
    cp_IWtype:            cross priv_mode_m, IWtype;
    cp_IWshift:           cross priv_mode_m, IWshift;
    cp_store:             cross priv_mode_m, store;
    cp_fstore:            cross priv_mode_m, fstore;
    cp_atomic_funct3:     cross priv_mode_m, atomic_funct3;
    cp_atomic_funct7:     cross priv_mode_m, atomic_funct7;
    cp_lrsc:              cross priv_mode_m, lrsc;
    cp_Rtype:             cross priv_mode_m, Rtype;
    cp_RWtype:            cross priv_mode_m, RWtype;
    cp_Ftype:             cross priv_mode_m, Ftype;
    cp_fsqrt:             cross priv_mode_m, fsqrt;
    cp_fclass:            cross priv_mode_m, fclass;
    cp_fcvtif:            cross priv_mode_m, fcvtif;
    cp_fcvtif_fmt:        cross priv_mode_m, fcvtif_fmt;
    cp_fcvtfi:            cross priv_mode_m, fcvtfi;
    cp_fcvtfi_fmt:        cross priv_mode_m, fcvtfi_fmt;
    cp_fcvtff:            cross priv_mode_m, fcvtff;
    cp_fcvtff_fmt:        cross priv_mode_m, fcvtff_fmt;
    cp_fmvif:             cross priv_mode_m, fmvif;
    cp_fmvfi:             cross priv_mode_m, fmvfi;
    cp_fli:               cross priv_mode_m, fli;
    cp_fmvh:              cross priv_mode_m, fmvh;
    cp_fmvp:              cross priv_mode_m, fmvp;
    cp_cvtmodwd:          cross priv_mode_m, cvtmodwd;
    cp_cvtmodwdfrm:       cross priv_mode_m, cvtmodwdfrm;
    cp_branch:            cross priv_mode_m, branch;
    cp_jalr:              cross priv_mode_m, jalr;
    cp_privileged_funct3: cross priv_mode_m, privileged_funct3;
    cp_privileged_000:    cross priv_mode_m, privileged_000;
    cp_privileged_rd:     cross priv_mode_m, privileged_rd;
    cp_privileged_rs2:    cross priv_mode_m, privileged_rs2;
    cp_reserved:          cross priv_mode_m, reserved;
    cp_upperreg_rs1:      cross priv_mode_m, upperreg_rs1;
    cp_upperreg_rs2:      cross priv_mode_m, upperreg_rs2;
    cp_upperreg_rd:       cross priv_mode_m, upperreg_rd;
    cp_upperreg_imm_rd:   cross priv_mode_m, upperreg_imm_rd;
    cp_upperreg_imm_rs1:  cross priv_mode_m, upperreg_imm_rs1;
    cp_upperreg_fmv_rs1 : cross priv_mode_m, upperreg_fmv_rs1;
    cp_upperreg_fmv_rd :  cross priv_mode_m, upperreg_fmv_rd;
    cp_amocas_odd :       cross priv_mode_m, amocas_odd;
    cp_reserved_rm :      cross priv_mode_m, reserved_rm;

    // ── Vector coverpoints crossed with priv_mode_m ──────────────────
    // Definitions are in RISCV_coverage_vect_instr.svh; only the cross
    // with privilege mode belongs here.

    // vset* reserved encodings
    cp_v_vsetvl:          cross priv_mode_m, v_vsetvl;
    cp_v_vsetvli_sew:     cross priv_mode_m, v_vsetvli_sew;
    cp_v_vsetvli_res:     cross priv_mode_m, v_vsetvli_res;
    cp_v_vsetivli_sew:    cross priv_mode_m, v_vsetivli_sew;
    cp_v_vsetivli_res:    cross priv_mode_m, v_vsetivli_res;

    // Vector load/store reserved encodings
    cp_vl_width:          cross priv_mode_m, vl_width;
    cp_vl_lumop:          cross priv_mode_m, vl_lumop;
    cp_vs_width:          cross priv_mode_m, vs_width;
    cp_vs_sumop:          cross priv_mode_m, vs_sumop;

    // Vector arithmetic funct6 × SEW
    cp_v_IVV_f6:          cross priv_mode_m, v_IVV_f6, current_vsew;
    cp_v_FVV_f6:          cross priv_mode_m, v_FVV_f6, current_vsew;
    cp_v_MVV_f6:          cross priv_mode_m, v_MVV_f6, current_vsew;
    cp_v_IVI_f6:          cross priv_mode_m, v_IVI_f6, current_vsew;
    cp_v_IVX_f6:          cross priv_mode_m, v_IVX_f6, current_vsew;
    cp_v_FVF_f6:          cross priv_mode_m, v_FVF_f6, current_vsew;
    cp_v_MVX_f6:          cross priv_mode_m, v_MVX_f6, current_vsew;

    // Vector unary instructions
    cp_v_VWRXUNARY0:      cross priv_mode_m, v_VWRXUNARY0, current_vsew;
    cp_v_VRXUNARY0:       cross priv_mode_m, v_VRXUNARY0, current_vsew;
    cp_v_VXUNARY0:        cross priv_mode_m, v_VXUNARY0, current_vsew;
    cp_v_VMUNARY0:        cross priv_mode_m, v_VMUNARY0, current_vsew;
    cp_v_VWFUNARY0:       cross priv_mode_m, v_VWFUNARY0, current_vsew;
    cp_v_VRFUNARY0:       cross priv_mode_m, v_VRFUNARY0, current_vsew;
    cp_v_VFUNARY0:        cross priv_mode_m, v_VFUNARY0, current_vsew;
    cp_v_VFUNARY1:        cross priv_mode_m, v_VFUNARY1, current_vsew;

    // Vector crypto
    cp_v_vaesvv:          cross priv_mode_m, v_vaesvv, current_vsew;
    cp_v_vaesvs:          cross priv_mode_m, v_vaesvs, current_vsew;

endgroup

covergroup SsstrictSm_comp_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/RISCV_coverage_comp_instr.svh"

    // compressed00: generator excludes rd' = x8 (insn[4:2]=000, i.e. bits[2:0]
    // of insn[15:2] = 000) to protect the scratch base pointer.
    cp_compressed00: cross priv_mode_m, compressed00 {
        wildcard ignore_bins rd_p_x8 = binsof(compressed00) intersect {14'b???????????000};
        // Ignore memory operations that throw exceptions for bad addresses
        wildcard ignore_bins c_fld = binsof(compressed00) intersect {14'b001??????000};
        wildcard ignore_bins c_lw  = binsof(compressed00) intersect {14'b010??????000};
        wildcard ignore_bins c_lbu = binsof(compressed00) intersect {14'b10000?????000};
        wildcard ignore_bins c_lh  = binsof(compressed00) intersect {14'b100001????000};
        wildcard ignore_bins c_sb  = binsof(compressed00) intersect {14'b10001?????000};
        wildcard ignore_bins c_sh  = binsof(compressed00) intersect {14'b1000110???000};
        wildcard ignore_bins c_fsd = binsof(compressed00) intersect {14'b101??????000};
        wildcard ignore_bins c_sw  = binsof(compressed00) intersect {14'b110??????000};
    }

    // compressed01: generator excludes rd=x2 for CI-type instructions.
    // CI-type has funct3 ∈ {000, 010, 011} (bits[15:13]).  For other funct3
    // values the bits[11:7] field encodes something else, so the exclusion
    // only applies to CI-type.
    cp_compressed01: cross priv_mode_m, compressed01 {
        // rd=x2 only for CI-type (funct3 = 000, 010, 011)
        wildcard ignore_bins rd_x2_ci_000 = binsof(compressed01) intersect {[14'b00000001000000:14'b00000001011111]};
        wildcard ignore_bins rd_x2_ci_010 = binsof(compressed01) intersect {[14'b01000001000000:14'b01000001011111]};
        wildcard ignore_bins rd_x2_ci_011 = binsof(compressed01) intersect {[14'b01100001000000:14'b01100001011111]};
        // Ignore control flow instructions that would break test execution
        wildcard ignore_bins c_jal = binsof(compressed01) intersect {14'b001????01};
        wildcard ignore_bins c_j   = binsof(compressed01) intersect {14'b101????01};
        wildcard ignore_bins c_beqz_bnez = binsof(compressed01) intersect {14'b11??????01};
    }

    // compressed10: generator excludes rd=x2 and rd=x8.
    // In quadrant 10, bit[15]=1 is fixed in the template "1EEEEEEEEEEEEE10",
    // so only the upper half of the encoding space is swept.
    cp_compressed10: cross priv_mode_m, compressed10 {
        // Ignore lower half (bit[15]=0) - not swept by generator
        wildcard ignore_bins lower_half = binsof(compressed10) intersect {14'b0???????????10};
        // rd=x2(sp) for the swept portion (bit[15]=1): insn[11:7]=00010
        wildcard ignore_bins rd_x2 = binsof(compressed10) intersect {14'b1???00010?????};
        // rd=x8 for the swept portion
        wildcard ignore_bins rd_x8 = binsof(compressed10) intersect {14'b1???01000?????};
        // Ignore floating-point/stack operations that throw exceptions
        wildcard ignore_bins c_fldsp = binsof(compressed10) intersect {14'b1001??????????};
        wildcard ignore_bins c_lwsp  = binsof(compressed10) intersect {14'b10010?????????};
        wildcard ignore_bins c_jr    = binsof(compressed10) intersect {14'b1000000000????};
        wildcard ignore_bins c_jalr  = binsof(compressed10) intersect {14'b1001000000????};
        wildcard ignore_bins c_fsdsp = binsof(compressed10) intersect {14'b1101??????????};
        wildcard ignore_bins c_swsp  = binsof(compressed10) intersect {14'b1110??????????};
    }
endgroup

function void ssstrictsm_sample(int hart, int issue, ins_t ins);
    SsstrictSm_instr_cg.sample(ins);
    SsstrictSm_comp_instr_cg.sample(ins);
    SsstrictSm_mcsr_cg.sample(ins);
endfunction
