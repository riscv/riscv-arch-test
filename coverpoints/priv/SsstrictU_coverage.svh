///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 23 March 2025
// Updated: cp_misa_ext_disable added per Ssstrict testplan completion
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSSTRICTU

// ============================================================================
// SsstrictU_ucsr_cg
// Goal: Verify all 4096 CSR addresses are read, written (0s/1s), set, and
//       cleared from user mode. Only user-level CSRs (cycle, time, instret,
//       fflags, frm, fcsr) should succeed; all others trap.
// Exclusions: User-custom CSRs only (0x800-0x8FF, 0xCC0-0xCFF).
// ============================================================================
covergroup SsstrictU_ucsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // ── building blocks ──────────────────────────────────────────────────────

    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] };
    }
    csrr: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b????????????_00000_010_?????_1110011};
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b????????????_?????_001_?????_1110011};
    }
    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }
    rs1_ones: coverpoint ins.current.rs1_val {
        bins ones = {'1};
    }
    rs1_edges: coverpoint ins.current.rs1_val {
        bins zero = {0};
        bins ones = {'1};
    }

    // All 4096 CSR addresses — U-mode exclusions: only user-custom ranges
    csr: coverpoint ins.current.insn[31:20] {
        bins user_std0[]        = {[12'h000:12'h0FF]};
        bins super_std0[]       = {[12'h100:12'h17F]};
        bins super_std0b[]      = {[12'h180:12'h1FF]};  // includes satp — traps from U-mode
        bins hyper_std0[]       = {[12'h200:12'h2FF]};
        bins mach_std0[]        = {[12'h300:12'h3FF]};  // all trap from U-mode
        bins user_std1[]        = {[12'h400:12'h4FF]};
        bins super_std1[]       = {[12'h500:12'h5BF]};
        bins super_cust1[]      = {[12'h5C0:12'h5FF]};  // tested from U-mode (may trap)
        bins hyper_std1[]       = {[12'h600:12'h6BF]};
        bins hyper_cust1[]      = {[12'h6C0:12'h6FF]};
        bins mach_std1[]        = {[12'h700:12'h7AF]};
        bins mach_debug[]       = {[12'h7A0:12'h7AF]};
        bins debug_only[]       = {[12'h7B0:12'h7BF]};
        bins mach_cust1[]       = {[12'h7C0:12'h7FF]};
        ignore_bins user_cust2  = {[12'h800:12'h8FF]};  // skip user-custom
        bins super_std2[]       = {[12'h900:12'h9BF]};
        bins super_cust2[]      = {[12'h9C0:12'h9FF]};
        bins hyper_std2[]       = {[12'hA00:12'hABF]};
        bins hyper_cust2[]      = {[12'hAC0:12'hAFF]};
        bins mach_std2[]        = {[12'hB00:12'hBBF]};
        bins mach_cust2[]       = {[12'hBC0:12'hBFF]};
        bins user_std3[]        = {[12'hC00:12'hCBF]};
        ignore_bins user_cust3  = {[12'hCC0:12'hCFF]};  // skip user-custom
        bins super_std3[]       = {[12'hD00:12'hDBF]};
        bins super_cust3[]      = {[12'hDC0:12'hDFF]};
        bins hyper_std3[]       = {[12'hE00:12'hEBF]};
        bins hyper_cust3[]      = {[12'hEC0:12'hEFF]};
        bins mach_std3[]        = {[12'hF00:12'hFBF]};
        bins mach_cust3[]       = {[12'hFC0:12'hFFF]};
    }

    // ── main coverpoints ─────────────────────────────────────────────────────

    // Read every CSR from U-mode
    cp_csrr:       cross priv_mode_u, csrr,  csr, nonzerord;

    // Write all-zeros and all-ones to every CSR from U-mode
    cp_csrw_edges: cross priv_mode_u, csrrw, csr, rs1_edges;

    // Set and clear every CSR from U-mode
    cp_csrcs:      cross priv_mode_u, csrop, csr, rs1_ones;

endgroup


// ============================================================================
// SsstrictU_instr_cg
// Goal: Verify all reserved/illegal 32-bit instruction encodings cause the
//       correct response when executed in U-mode. Same encoding space as
//       SsstrictSm/S but the privilege mode cross uses priv_mode_u.
// ============================================================================
covergroup SsstrictU_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_instr.svh"

    // ── main coverpoints ─────────────────────────────────────────────────────
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
    cp_upperreg_fmv_rs1:  cross priv_mode_u, upperreg_fmv_rs1;
    cp_upperreg_fmv_rd:   cross priv_mode_u, upperreg_fmv_rd;
    cp_amocas_odd:        cross priv_mode_u, amocas_odd;
    cp_reserved_rm:       cross priv_mode_u, reserved_rm;

    // ── cp_misa_ext_disable (U-mode) ─────────────────────────────────────────
    // Verify instructions from disabled extensions trap when executed in U-mode.

    misa_val: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "misa") {
        type_option.weight = 0;
        bins misa_A_clear = {32'b?????????????????????????????_?_0_?????};
        bins misa_B_clear = {32'b????????????????????????????_?_0_??????};
        bins misa_C_clear = {32'b???????????????????????????_?_0_???????};
        bins misa_D_clear = {32'b??????????????????????????_?_0_????????};
        bins misa_F_clear = {32'b????????????????????????_?_0_??????????};
        bins misa_M_clear = {32'b???????????????????_?_0_???????????????};
        bins misa_V_clear = {32'b??????????_?_0_?????????????????????};
    }

    misa_disable_instr: coverpoint ins.current.insn {
        wildcard bins misa_A_instr     = {32'b00001_??_?????_?????_010_?????_0101111};
        wildcard bins misa_C_instr     = {32'b?????_?_?????_?????_?????_???_01};
        wildcard bins misa_D_instr     = {32'b0000001_?????_?????_???_?????_1010011};
        wildcard bins misa_F_instr     = {32'b0000000_?????_?????_???_?????_1010011};
        wildcard bins misa_M_instr     = {32'b0000001_?????_?????_000_?????_0110011};
        wildcard bins misa_V_instr     = {32'b000000_?_?????_?????_000_?????_1010111};
        wildcard bins misa_B_zba_instr = {32'b0010000_?????_?????_110_?????_0110011};
        wildcard bins misa_B_zbb_instr = {32'b0100000_?????_?????_111_?????_0110011};
        wildcard bins misa_B_zbs_instr = {32'b0100100_?????_?????_101_?????_0110011};
        wildcard bins misa_I_upperreg  = {32'b????????????_1????_000_?????_0010011};
    }

    cp_misa_ext_disable: cross priv_mode_u, misa_disable_instr, misa_val;

endgroup


// ============================================================================
// SsstrictU_comp_instr_cg
// Goal: All 2^14 compressed encodings in each quadrant, exercised from U-mode.
// ============================================================================
covergroup SsstrictU_comp_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_comp_instr.svh"

    cp_compressed00: cross priv_mode_u, compressed00;
    cp_compressed01: cross priv_mode_u, compressed01;
    cp_compressed10: cross priv_mode_u, compressed10;

endgroup


// ============================================================================
// Sample function
// ============================================================================
function void ssstrictu_sample(int hart, int issue, ins_t ins);
    SsstrictU_ucsr_cg.sample(ins);
    SsstrictU_instr_cg.sample(ins);
    SsstrictU_comp_instr_cg.sample(ins);
endfunction
