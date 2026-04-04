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

`define COVER_SSSTRICTS

// ============================================================================
// SsstrictS_scsr_cg
// Goal: Verify all 4096 CSR addresses are read, written (0s/1s), set, and
//       cleared from supervisor mode. Also verifies mstatus/sstatus shadow
//       register consistency (mie/sie, mip/sip).
// Exclusions: satp (0x180 — would enable virtual memory), all custom ranges.
// ============================================================================
covergroup SsstrictS_scsr_cg with function sample(ins_t ins);
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

    // All 4096 CSR addresses, S-mode exclusions:
    // - satp (0x180) excluded to prevent accidentally enabling virtual memory
    // - All custom CSR ranges excluded
    csr: coverpoint ins.current.insn[31:20] {
        bins user_std0[]        = {[12'h000:12'h0FF]};
        bins super_std0[]       = {[12'h100:12'h17F]};
        ignore_bins satp        = {12'h180};              // satp — skip, tested in VM tests
        bins super_std0b[]      = {[12'h181:12'h1FF]};
        bins hyper_std0[]       = {[12'h200:12'h2FF]};
        bins mach_std0[]        = {[12'h300:12'h3FF]};   // M-mode CSRs — should trap from S-mode
        bins user_std1[]        = {[12'h400:12'h4FF]};
        bins super_std1[]       = {[12'h500:12'h5BF]};
        ignore_bins super_cust1 = {[12'h5C0:12'h5FF]};
        bins hyper_std1[]       = {[12'h600:12'h6BF]};
        ignore_bins hyper_cust1 = {[12'h6C0:12'h6FF]};
        bins mach_std1[]        = {[12'h700:12'h7AF]};
        bins mach_debug[]       = {[12'h7A0:12'h7AF]};   // Debug trigger regs — trap from S-mode
        bins debug_only[]       = {[12'h7B0:12'h7BF]};   // Debug-only — trap from S-mode
        bins mach_cust1[]       = {[12'h7C0:12'h7FF]};   // M-mode custom — trap from S-mode
        ignore_bins user_cust2  = {[12'h800:12'h8FF]};
        bins super_std2[]       = {[12'h900:12'h9BF]};
        ignore_bins super_cust2 = {[12'h9C0:12'h9FF]};
        bins hyper_std2[]       = {[12'hA00:12'hABF]};
        ignore_bins hyper_cust2 = {[12'hAC0:12'hAFF]};
        bins mach_std2[]        = {[12'hB00:12'hBBF]};
        bins mach_cust2[]       = {[12'hBC0:12'hBFF]};   // M-mode custom — trap from S-mode
        bins user_std3[]        = {[12'hC00:12'hCBF]};
        ignore_bins user_cust3  = {[12'hCC0:12'hCFF]};
        bins super_std3[]       = {[12'hD00:12'hDBF]};
        ignore_bins super_cust3 = {[12'hDC0:12'hDFF]};
        bins hyper_std3[]       = {[12'hE00:12'hEBF]};
        ignore_bins hyper_cust3 = {[12'hEC0:12'hEFF]};
        bins mach_std3[]        = {[12'hF00:12'hFBF]};
        bins mach_cust3[]       = {[12'hFC0:12'hFFF]};   // M-mode custom — trap from S-mode
    }

    // Shadow register pairs: M-mode side (written from M-mode)
    mcsrs: coverpoint ins.current.insn[31:20] {
        bins mstatus = {12'h300};
        bins mie     = {12'h304};
        bins mip     = {12'h344};
    }

    // Shadow register pairs: S-mode side (written from S-mode)
    scsrs: coverpoint ins.current.insn[31:20] {
        bins sstatus = {12'h100};
        bins sie     = {12'h104};
        bins sip     = {12'h144};
    }

    // ── main coverpoints ─────────────────────────────────────────────────────

    // Read every CSR from S-mode
    cp_csrr:       cross priv_mode_s, csrr,  csr, nonzerord;

    // Write all-zeros and all-ones to every CSR from S-mode
    cp_csrw_edges: cross priv_mode_s, csrrw, csr, rs1_edges;

    // Set and clear every CSR from S-mode
    cp_csrcs:      cross priv_mode_s, csrop, csr, rs1_ones;

    // Shadow consistency: write 0s/1s to mstatus/mie/mip from M-mode
    // (verifies that the M-mode write is reflected in sstatus/sie/sip)
    cp_shadow_m:   cross priv_mode_m, csrrw, mcsrs, rs1_edges;

    // Shadow consistency: write 0s/1s to sstatus/sie/sip from S-mode
    // (verifies that the S-mode write is reflected in mstatus/mie/mip)
    cp_shadow_s:   cross priv_mode_s, csrrw, scsrs, rs1_edges;

endgroup


// ============================================================================
// SsstrictS_instr_cg
// Goal: Verify all reserved/illegal 32-bit instruction encodings cause the
//       correct response when executed in S-mode. Same encoding space as
//       SsstrictSm but the privilege mode cross uses priv_mode_s.
// ============================================================================
covergroup SsstrictS_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_instr.svh"

    // ── main coverpoints ─────────────────────────────────────────────────────
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
    cp_cvtmodwdfrm:       cross priv_mode_s, cvtmodwdfrm;
    cp_branch:            cross priv_mode_s, branch;
    cp_jalr:              cross priv_mode_s, jalr;
    cp_privileged_funct3: cross priv_mode_s, privileged_funct3;
    cp_privileged_000:    cross priv_mode_s, privileged_000;
    cp_privileged_rd:     cross priv_mode_s, privileged_rd;
    cp_privileged_rs2:    cross priv_mode_s, privileged_rs2;
    cp_reserved:          cross priv_mode_s, reserved;
    cp_upperreg_rs1:      cross priv_mode_s, upperreg_rs1;
    cp_upperreg_rs2:      cross priv_mode_s, upperreg_rs2;
    cp_upperreg_rd:       cross priv_mode_s, upperreg_rd;
    cp_upperreg_imm_rd:   cross priv_mode_s, upperreg_imm_rd;
    cp_upperreg_imm_rs1:  cross priv_mode_s, upperreg_imm_rs1;
    cp_upperreg_fmv_rs1:  cross priv_mode_s, upperreg_fmv_rs1;
    cp_upperreg_fmv_rd:   cross priv_mode_s, upperreg_fmv_rd;
    cp_amocas_odd:        cross priv_mode_s, amocas_odd;
    cp_reserved_rm:       cross priv_mode_s, reserved_rm;

    // ── cp_misa_ext_disable (S-mode) ─────────────────────────────────────────
    // Verify instructions from disabled extensions trap when executed in S-mode.
    // misa is set from M-mode before switching to S-mode; instruction executed
    // in S-mode. Bins mirror those in SsstrictSm_instr_cg.

    misa_val: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "misa") {
        type_option.weight = 0;
        bins misa_A_clear = {32'b?????????????????????????????_?_0_?????};
        bins misa_B_clear = {32'b????????????????????????????_?_0_??????};
        bins misa_C_clear = {32'b???????????????????????????_?_0_???????};
        bins misa_D_clear = {32'b??????????????????????????_?_0_????????};
        bins misa_F_clear = {32'b????????????????????????_?_0_??????????};
        bins misa_M_clear = {32'b???????????????????_?_0_???????????????};
        bins misa_U_clear = {32'b?????????_?_0_???????????????????};   // bit 20 = U
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
        // Attempt to enter U-mode with misa.U=0: ecall(0) from S-mode
        // This is captured as an ecall with a0=0 executed in S-mode
        wildcard bins misa_U_ecall     = {32'b00000000000000000000000001110011};
        wildcard bins misa_I_upperreg  = {32'b????????????_1????_000_?????_0010011};
    }

    cp_misa_ext_disable: cross priv_mode_s, misa_disable_instr, misa_val;

endgroup


// ============================================================================
// SsstrictS_comp_instr_cg
// Goal: All 2^14 compressed encodings in each quadrant, exercised from S-mode.
// ============================================================================
covergroup SsstrictS_comp_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_comp_instr.svh"

    cp_compressed00: cross priv_mode_s, compressed00;
    cp_compressed01: cross priv_mode_s, compressed01;
    cp_compressed10: cross priv_mode_s, compressed10;

endgroup


// ============================================================================
// Sample function
// ============================================================================
function void ssstricts_sample(int hart, int issue, ins_t ins);
    SsstrictS_scsr_cg.sample(ins);
    SsstrictS_instr_cg.sample(ins);
    SsstrictS_comp_instr_cg.sample(ins);
endfunction
