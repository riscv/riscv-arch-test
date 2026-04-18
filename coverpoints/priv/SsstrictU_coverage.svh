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
        wildcard bins csrr = {32'b????????????_00000_010_?????_1110011};
    }
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b????????????_?????_001_?????_1110011};
    }
    // Similar to SsstrictSm/S, but exercises all CSRs except user custom.
    csr: coverpoint ins.current.insn[31:20]  {
        bins user_std0[] = {[12'h000:12'h0FF]};
        bins super_std0[] = {[12'h100:12'h17F]};
        bins super_std02[] = {[12'h180:12'h1FF]};
        bins hyper_std0[] = {[12'h200:12'h2FF]};
        bins mach_std0[] = {[12'h300:12'h3FF]};
        bins user_std1[] = {[12'h400:12'h4FF]};
        bins super_std1[] = {[12'h500:12'h5BF]};
        bins super_custom1 = {[12'h5C0:12'h5FF]};
        bins hyper_std1[] = {[12'h600:12'h6BF]};
        bins hyper_custom1 = {[12'h6C0:12'h6FF]};
        bins mach_std1[] = {[12'h700:12'h7AF]};
        bins mach_debug[] = {[12'h7A0:12'h7AF]};
        bins debug_only[] = {[12'h7B0:12'h7BF]};
        bins mach_custom1[] = {[12'h7C0:12'h7FF]};
        ignore_bins user_custom2 = {[12'h800:12'h8FF]};
        bins super_std2[] = {[12'h900:12'h9BF]};
        bins super_custom22 = {[12'h9C0:12'h9FF]};
        bins hyper_std2[] = {[12'hA00:12'hABF]};
        bins hyper_custom22 = {[12'hAC0:12'hAFF]};
        bins mach_std2[] = {[12'hB00:12'hBBF]};
        bins mach_custom2[] = {[12'hBC0:12'hBFF]};
        bins user_std3[] = {[12'hC00:12'hCBF]};
        ignore_bins user_custom3 = {[12'hCC0:12'hCFF]};
        bins super_std3[] = {[12'hD00:12'hDBF]};
        bins super_custom3 = {[12'hDC0:12'hDFF]};
        bins hyper_std3[] = {[12'hE00:12'hEBF]};
        bins hyper_custom3 = {[12'hEC0:12'hEFF]};
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

    // main coverpoints
    cp_csrr:       cross csrr,  csr,   priv_mode_u, nonzerord;
    cp_csrw_edges: cross csrrw, csr,   priv_mode_u, rs1_edges;
    cp_csrcs:      cross csrop, csr,   priv_mode_u, rs1_ones;
endgroup

covergroup SsstrictU_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RISCV_coverage_instr.svh"

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
    cp_reserved_rm :      cross priv_mode_u, reserved_rm;

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



covergroup SsstrictU_misa_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // Which misa extension bit was disabled when the instruction executed
    misa_val: coverpoint ins.current.csr[12'h301] {
        wildcard bins misa_A_off = {64'b???????????????????????????????????????????????????????????????????????0}; // bit 0
        wildcard bins misa_C_off = {64'b?????????????????????????????????????????????????????????????????????0??}; // bit 2
        wildcard bins misa_D_off = {64'b????????????????????????????????????????????????????????????????????0???}; // bit 3
        wildcard bins misa_F_off = {64'b??????????????????????????????????????????????????????????????????0?????}; // bit 5
        wildcard bins misa_M_off = {64'b?????????????????????????????????????????????????????????????????0????????????}; // bit 12
        wildcard bins misa_B_off = {64'b?????????????????????????????????????????????????????????????????????????????0?}; // bit 1
        wildcard bins misa_I_off = {64'b????????????????????????????????????????????????????????????????????????0????????}; // bit 8
    }

    // Representative instruction for each disabled extension — named bins per instruction
    misa_disable_instr: coverpoint ins.current.insn {
        // A extension: amoswap.w (op=0101111, funct3=010, funct5=00001)
        wildcard bins amoswap_w = {32'b00001_??_?????_?????_010_?????_0101111};
        // C extension: c.addi (op=01, funct3=000)
        wildcard bins c_addi    = {16'b000_?_?????_?????_01};
        // D extension: fadd.d (op=1010011, funct7=0000001)
        wildcard bins fadd_d    = {32'b0000001_?????_?????_000_?????_1010011};
        // F extension: fadd.s (op=1010011, funct7=0000000)
        wildcard bins fadd_s    = {32'b0000000_?????_?????_000_?????_1010011};
        // M extension: mul (op=0110011, funct7=0000001, funct3=000)
        wildcard bins mul       = {32'b0000001_?????_?????_000_?????_0110011};
        // B/Zba extension: sh3add (op=0110011, funct7=0010000, funct3=110)
        wildcard bins sh3add    = {32'b0010000_?????_?????_110_?????_0110011};
        // B/Zbb extension: andn (op=0110011, funct7=0100000, funct3=111)
        wildcard bins andn      = {32'b0100000_?????_?????_111_?????_0110011};
        // B/Zbs extension: bext (op=0110011, funct7=0100100, funct3=101)
        wildcard bins bext      = {32'b0100100_?????_?????_101_?????_0110011};
        // I/E extension: add with upper register (x16-x31 as rs1)
        wildcard bins add_upper = {32'b0000000_?????_1????_000_?????_0110011};
    }

    // Cross: which misa bit was off × which instruction × privilege mode
    cp_misa_ext_disable: cross priv_mode_u, misa_disable_instr, misa_val;
endgroup

function void ssstrictu_sample(int hart, int issue, ins_t ins);
    SsstrictU_ucsr_cg.sample(ins);
    SsstrictU_instr_cg.sample(ins);
    SsstrictU_comp_instr_cg.sample(ins);
    SsstrictU_misa_cg.sample(ins);
endfunction
