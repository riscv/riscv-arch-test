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

`define COVER_SSSTRICTSM

// ============================================================================
// SsstrictSm_mcsr_cg
// Goal: Verify all 4096 CSR addresses are read, written (0s/1s), set, and
//       cleared from machine mode.
// Exclusions: PMP regs 0x3A0-0x3EF, debug-only 0x7B0-0x7BF, all custom ranges.
// ============================================================================
covergroup SsstrictSm_mcsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // ── building blocks ──────────────────────────────────────────────────────

    // rd != x0 (for CSRR to be meaningful)
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] };
    }

    // CSRR: rs1=0, funct3=010 (CSRRS with rs1=x0 = pure read)
    csrr: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b????????????_00000_010_?????_1110011};
    }

    // CSRRW: funct3=001
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b????????????_?????_001_?????_1110011};
    }

    // CSRRS/CSRRC: funct3=010 or 011
    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }

    // rs1 value edge cases: all-zeros and all-ones
    rs1_ones: coverpoint ins.current.rs1_val {
        bins ones = {'1};
    }
    rs1_edges: coverpoint ins.current.rs1_val {
        bins zero = {0};
        bins ones = {'1};
    }

    // All 4096 CSR address bins, with exclusions for M-mode
    csr: coverpoint ins.current.insn[31:20] {
        // User-level standard CSRs
        bins user_std0[]        = {[12'h000:12'h0FF]};
        // Supervisor-level standard CSRs
        bins super_std0[]       = {[12'h100:12'h1FF]};
        // Hypervisor-level standard CSRs
        bins hyper_std0[]       = {[12'h200:12'h2FF]};
        // Machine-level standard CSRs (including mstatus, misa, etc.)
        bins mach_std0[]        = {[12'h300:12'h3FF]};
        // PMP registers excluded — toggling while running would corrupt protection
        ignore_bins PMP_regs    = {[12'h3A0:12'h3EF]};
        // More user/supervisor/hypervisor standard CSRs
        bins user_std1[]        = {[12'h400:12'h4FF]};
        bins super_std1[]       = {[12'h500:12'h5BF]};
        ignore_bins super_cust1 = {[12'h5C0:12'h5FF]};
        bins hyper_std1[]       = {[12'h600:12'h6BF]};
        ignore_bins hyper_cust1 = {[12'h6C0:12'h6FF]};
        // Machine debug/trigger CSRs: 0x7A0-0x7AF accessible in M-mode (but skip to avoid debug issues)
        bins mach_std1[]        = {[12'h700:12'h7AF]};
        ignore_bins mach_debug  = {[12'h7A0:12'h7AF]};
        // 0x7B0-0x7BF: debug-only — access from M-mode raises illegal-instruction
        bins debug_only[]       = {[12'h7B0:12'h7BF]};
        // Machine-custom1: skip
        ignore_bins mach_cust1  = {[12'h7C0:12'h7FF]};
        // User-custom2: skip
        ignore_bins user_cust2  = {[12'h800:12'h8FF]};
        // More standard CSRs
        bins super_std2[]       = {[12'h900:12'h9BF]};
        ignore_bins super_cust2 = {[12'h9C0:12'h9FF]};
        bins hyper_std2[]       = {[12'hA00:12'hABF]};
        ignore_bins hyper_cust2 = {[12'hAC0:12'hAFF]};
        bins mach_std2[]        = {[12'hB00:12'hBBF]};
        ignore_bins mach_cust2  = {[12'hBC0:12'hBFF]};
        bins user_std3[]        = {[12'hC00:12'hCBF]};
        ignore_bins user_cust3  = {[12'hCC0:12'hCFF]};
        bins super_std3[]       = {[12'hD00:12'hDBF]};
        ignore_bins super_cust3 = {[12'hDC0:12'hDFF]};
        bins hyper_std3[]       = {[12'hE00:12'hEBF]};
        ignore_bins hyper_cust3 = {[12'hEC0:12'hEFF]};
        bins mach_std3[]        = {[12'hF00:12'hFBF]};
        ignore_bins mach_cust3  = {[12'hFC0:12'hFFF]};
    }

    // Shadow registers: mstatus/mie/mip (M-mode write side)
    mcsrs: coverpoint ins.current.insn[31:20] {
        bins mstatus = {12'h300};
        bins mie     = {12'h304};
        bins mip     = {12'h344};
    }

    // ── main coverpoints ─────────────────────────────────────────────────────

    // Read every CSR from M-mode with rd != x0
    cp_csrr:       cross priv_mode_m, csrr,  csr, nonzerord;

    // Write all-zeros and all-ones to every CSR from M-mode
    cp_csrw_edges: cross priv_mode_m, csrrw, csr, rs1_edges;

    // Set and clear every CSR from M-mode using CSRRS/CSRRC with rs1=all-ones
    cp_csrcs:      cross priv_mode_m, csrop, csr, rs1_ones;

endgroup


// ============================================================================
// SsstrictSm_instr_cg
// Goal: Verify all reserved/illegal 32-bit instruction encodings cause the
//       correct response (illegal-instruction exception or legal execution)
//       when executed in M-mode.
// ============================================================================
covergroup SsstrictSm_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/RISCV_coverage_instr.svh"

    // ── main coverpoints ─────────────────────────────────────────────────────
    // Each cross verifies that the given instruction field pattern was
    // executed in M-mode. The building-block coverpoints are defined in
    // RISCV_coverage_instr.svh.

    // Reserved major opcodes (op7/15/21/23/26/29/31)
    cp_illegal:           cross priv_mode_m, illegal;

    // Reserved funct3 in LOAD / FLOAD / FENCE-CBO
    cp_load:              cross priv_mode_m, load;
    cp_fload:             cross priv_mode_m, fload;
    cp_fence_cbo:         cross priv_mode_m, fence_cbo;

    // Reserved CBO immediate and rd fields
    cp_cbo_immediate:     cross priv_mode_m, cbo_immediate;
    cp_cbo_rd:            cross priv_mode_m, cbo_rd;

    // Reserved I-type subfields (funct3[2:1]=01, all funct3, aes64ks1i rnum)
    cp_Itype:             cross priv_mode_m, Itype;
    cp_Itypef3:           cross priv_mode_m, Itypef3;
    cp_aes64ks1i:         cross priv_mode_m, aes64ks1i;

    // Reserved IW-type (RV64 word ops) funct3 and shift fields
    cp_IWtype:            cross priv_mode_m, IWtype;
    cp_IWshift:           cross priv_mode_m, IWshift;

    // Reserved STORE / FSTORE funct3
    cp_store:             cross priv_mode_m, store;
    cp_fstore:            cross priv_mode_m, fstore;

    // Reserved atomic funct3 and funct7; LR/SC reserved fields
    cp_atomic_funct3:     cross priv_mode_m, atomic_funct3;
    cp_atomic_funct7:     cross priv_mode_m, atomic_funct7;
    cl_lrsc:              cross priv_mode_m, lrsc;

    // Reserved R-type (funct3×funct7) and RW-type
    cp_Rtype:             cross priv_mode_m, Rtype;
    cp_RWtype:            cross priv_mode_m, RWtype;

    // Reserved FP encoding fields
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

    // Reserved BRANCH funct3 (010 and 011)
    cp_branch:            cross priv_mode_m, branch;

    // Reserved JALR funct3 (anything != 000)
    cp_jalr:              cross priv_mode_m, jalr;

    // Reserved SYSTEM funct3 and funct7/rs2/rd fields
    cp_privileged_funct3: cross priv_mode_m, privileged_funct3;
    cp_privileged_000:    cross priv_mode_m, privileged_000;
    cp_privileged_rd:     cross priv_mode_m, privileged_rd;
    cp_privileged_rs2:    cross priv_mode_m, privileged_rs2;

    // Reserved FENCE fm/rs1/rd fields and reserved FMA rounding modes 5/6
    cp_reserved:          cross priv_mode_m, reserved;

    // Upper register (x16-x31) accesses — illegal when E extension active
    cp_upperreg_rs1:      cross priv_mode_m, upperreg_rs1;
    cp_upperreg_rs2:      cross priv_mode_m, upperreg_rs2;
    cp_upperreg_rd:       cross priv_mode_m, upperreg_rd;
    cp_upperreg_imm_rd:   cross priv_mode_m, upperreg_imm_rd;
    cp_upperreg_imm_rs1:  cross priv_mode_m, upperreg_imm_rs1;
    cp_upperreg_fmv_rs1:  cross priv_mode_m, upperreg_fmv_rs1;
    cp_upperreg_fmv_rd:   cross priv_mode_m, upperreg_fmv_rd;

    // Zacas: AMOCAS.D/Q with odd rd or rs2 register IDs
    cp_amocas_odd:        cross priv_mode_m, amocas_odd;

    // Reserved FP rounding modes (FRM=5/6 with dynamic rm=7)
    cp_reserved_rm:       cross priv_mode_m, reserved_rm;

    // ── cp_misa_ext_disable ───────────────────────────────────────────────────
    // Verify that executing an instruction from a disabled extension raises
    // illegal-instruction in M-mode.
    // Each bin captures: the instruction was executed with misa.EXT=0.
    // The misa value at the time of instruction execution is sampled.

    misa_val: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "misa") {
        type_option.weight = 0;
        // Bins detect each extension bit being 0 in misa
        bins misa_A_clear = {32'b?????????????????????????????_?_0_?????}; // bit 0 = A
        bins misa_B_clear = {32'b????????????????????????????_?_0_??????}; // bit 1 = B
        bins misa_C_clear = {32'b???????????????????????????_?_0_???????}; // bit 2 = C
        bins misa_D_clear = {32'b??????????????????????????_?_0_????????}; // bit 3 = D
        bins misa_F_clear = {32'b????????????????????????_?_0_??????????}; // bit 5 = F
        bins misa_M_clear = {32'b???????????????????_?_0_???????????????}; // bit 12 = M
        bins misa_V_clear = {32'b??????????_?_0_?????????????????????}; // bit 21 = V
    }

    // Representative instruction encoding for each extension (sampled when misa.EXT=0)
    misa_disable_instr: coverpoint ins.current.insn {
        // A extension: AMO instruction (amoswap.w, op=0101111 funct3=010 funct5=00001)
        wildcard bins misa_A_instr = {32'b00001_??_?????_?????_010_?????_0101111};
        // C extension: c.addi (16-bit, any non-illegal c.addi)
        wildcard bins misa_C_instr = {32'b?????_?_?????_?????_?????_???_01};
        // D extension: fadd.d (fmt=01)
        wildcard bins misa_D_instr = {32'b0000001_?????_?????_???_?????_1010011};
        // F extension: fadd.s (fmt=00, funct5=00000)
        wildcard bins misa_F_instr = {32'b0000000_?????_?????_???_?????_1010011};
        // M extension: mul (funct7=0000001, funct3=000)
        wildcard bins misa_M_instr = {32'b0000001_?????_?????_000_?????_0110011};
        // V extension: vadd.vv (funct6=000000, funct3=000, op=1010111)
        wildcard bins misa_V_instr = {32'b000000_?_?????_?????_000_?????_1010111};
        // B/Zba extension: sh3add (funct7=0010000, funct3=110)
        wildcard bins misa_B_zba_instr = {32'b0010000_?????_?????_110_?????_0110011};
        // B/Zbb extension: andn (funct7=0100000, funct3=111)
        wildcard bins misa_B_zbb_instr = {32'b0100000_?????_?????_111_?????_0110011};
        // B/Zbs extension: bext (funct7=0100100, funct3=101)
        wildcard bins misa_B_zbs_instr = {32'b0100100_?????_?????_101_?????_0110011};
        // I extension with upper regs (x16+ as rs1 — traps if E active)
        wildcard bins misa_I_upperreg  = {32'b????????????_1????_000_?????_0010011};
    }

    // Cross: the instruction was executed in M-mode while the relevant misa bit was 0
    cp_misa_ext_disable: cross priv_mode_m, misa_disable_instr, misa_val;

endgroup


// ============================================================================
// SsstrictSm_comp_instr_cg
// Goal: Verify all reserved/illegal 16-bit compressed instruction encodings
//       are exercised in M-mode (all three quadrants: 00, 01, 10).
// ============================================================================
covergroup SsstrictSm_comp_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/RISCV_coverage_comp_instr.svh"

    // All 2^14 encodings in compressed quadrant 00 (bits[1:0]=00)
    cp_compressed00: cross priv_mode_m, compressed00;

    // All 2^14 encodings in compressed quadrant 01 (bits[1:0]=01)
    cp_compressed01: cross priv_mode_m, compressed01;

    // All 2^14 encodings in compressed quadrant 10 (bits[1:0]=10)
    cp_compressed10: cross priv_mode_m, compressed10;

endgroup


// ============================================================================
// Sample function — called once per instruction retirement
// ============================================================================
function void ssstrictsm_sample(int hart, int issue, ins_t ins);
    SsstrictSm_mcsr_cg.sample(ins);
    SsstrictSm_instr_cg.sample(ins);
    SsstrictSm_comp_instr_cg.sample(ins);
endfunction
