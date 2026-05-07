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
        ignore_bins mach_debug = {[12'h7A0:12'h7AF]}; // toggling debug registers could do weird stuff
        bins debug_only[] = {[12'h7B0:12'h7BF]}; // access to debug mode registers raises illegal instruction even in machine mode
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
        bins mach_std3[] = {[12'hF00:12'hFBF]};
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
    cp_csrr:         cross priv_mode_m, csrr,     csr,   nonzerord;   // CSR read of all 4096 registers
    cp_csrw_edges:   cross priv_mode_m, csrrw,    csr,   rs1_edges;   // CSR write of all 0s / all 1s to all 4096 registers
    cp_csrcs:        cross priv_mode_m, csrop,    csr,   rs1_ones;    // CSR clear and set of all bits of all registers
endgroup


covergroup SsstrictSm_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/RISCV_coverage_instr.svh"

    // main coverpoints
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

    // ── Vector illegal instruction coverpoints ───────────────────────

    // Vector vset* reserved encodings
    // vsetvl reserved: bit[31]=1, bits[30:26] swept exhaustively
    v_vsetvl : coverpoint ins.current.insn[30:26] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b111 & ins.current.insn[31] == 1'b1) {
        // 2^5 bins — only a subset are legal
    }
    cp_v_vsetvl: cross priv_mode_m, v_vsetvl;

    // vsetvli with reserved SEW: bit[31]=0, bit[24]=1 (reserved SEW high bit)
    v_vsetvli_sew : coverpoint ins.current.insn[23:22] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b111 & ins.current.insn[31] == 1'b0 & ins.current.insn[24] == 1'b1) {
        // 2^2 bins of reserved SEW values
    }
    cp_v_vsetvli_sew: cross priv_mode_m, v_vsetvli_sew;

    // vsetvli with reserved upper bits: bit[31]=0, bit[24]=0
    v_vsetvli_res : coverpoint ins.current.insn[30:28] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b111 & ins.current.insn[31] == 1'b0 & ins.current.insn[24] == 1'b0) {
        // 2^3 bins of reserved upper bits
    }
    cp_v_vsetvli_res: cross priv_mode_m, v_vsetvli_res;

    // vsetivli with reserved SEW: bits[31:30]=11, bit[24]=1
    v_vsetivli_sew : coverpoint ins.current.insn[23:22] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b111 & ins.current.insn[31:30] == 2'b11 & ins.current.insn[24] == 1'b1) {
        // 2^2 bins of reserved SEW values
    }
    cp_v_vsetivli_sew: cross priv_mode_m, v_vsetivli_sew;

    // vsetivli with reserved upper bits: bits[31:30]=11, bit[24]=0
    v_vsetivli_res : coverpoint ins.current.insn[29:28] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b111 & ins.current.insn[31:30] == 2'b11 & ins.current.insn[24] == 1'b0) {
        // 2^2 bins of reserved upper bits
    }
    cp_v_vsetivli_res: cross priv_mode_m, v_vsetivli_res;

    // Vector load reserved width/mew combinations (opcode 0000111)
    vl_width : coverpoint {ins.current.insn[28], ins.current.insn[14:12]} iff (ins.current.insn[6:0] == 7'b0000111) {
        // {mew, width[2:0]} — 4-bit field, 16 combinations
        // mew=0: width 000,101,110,111 are reserved if unsupported SEW
        // mew=1: all widths reserved
    }
    cp_vl_width: cross priv_mode_m, vl_width;

    // Vector load reserved lumop (nf[2]=1 selects unit-stride variants with lumop field)
    vl_lumop : coverpoint ins.current.insn[24:20] iff (ins.current.insn[6:0] == 7'b0000111 & ins.current.insn[28] == 1'b0 & ins.current.insn[26] == 1'b1) {
        // 2^5 bins — only 00000 (unit), 01000 (whole), 01011 (mask), 10000 (fault-only-first) legal
    }
    cp_vl_lumop: cross priv_mode_m, vl_lumop;

    // Vector store reserved width/mew combinations (opcode 0100111)
    vs_width : coverpoint {ins.current.insn[28], ins.current.insn[14:12]} iff (ins.current.insn[6:0] == 7'b0100111) {
        // same structure as loads
    }
    cp_vs_width: cross priv_mode_m, vs_width;

    // Vector store reserved sumop
    vs_sumop : coverpoint ins.current.insn[24:20] iff (ins.current.insn[6:0] == 7'b0100111 & ins.current.insn[28] == 1'b0 & ins.current.insn[26] == 1'b1) {
        // 2^5 bins — only 00000 (unit), 01000 (whole) legal for stores
    }
    cp_vs_sumop: cross priv_mode_m, vs_sumop;

    // Vector arithmetic funct6 sweeps (opcode 1010111, funct3 selects category)
    // Each funct6 bin covers all 64 possible function codes per category
    v_IVV_f6 : coverpoint ins.current.insn[31:26] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b000) {
        // OPIVV: all 64 funct6 values
    }
    cp_v_IVV_f6: cross priv_mode_m, v_IVV_f6;

    v_FVV_f6 : coverpoint ins.current.insn[31:26] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b001) {
        // OPFVV: all 64 funct6 values
    }
    cp_v_FVV_f6: cross priv_mode_m, v_FVV_f6;

    v_MVV_f6 : coverpoint ins.current.insn[31:26] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b010) {
        // OPMVV: all 64 funct6 values
    }
    cp_v_MVV_f6: cross priv_mode_m, v_MVV_f6;

    v_IVI_f6 : coverpoint ins.current.insn[31:26] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b011) {
        // OPIVI: all 64 funct6 values
    }
    cp_v_IVI_f6: cross priv_mode_m, v_IVI_f6;

    v_IVX_f6 : coverpoint ins.current.insn[31:26] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b100) {
        // OPIVX: all 64 funct6 values
    }
    cp_v_IVX_f6: cross priv_mode_m, v_IVX_f6;

    v_FVF_f6 : coverpoint ins.current.insn[31:26] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b101) {
        // OPFVF: all 64 funct6 values
    }
    cp_v_FVF_f6: cross priv_mode_m, v_FVF_f6;

    v_MVX_f6 : coverpoint ins.current.insn[31:26] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b110) {
        // OPMVX: all 64 funct6 values
    }
    cp_v_MVX_f6: cross priv_mode_m, v_MVX_f6;

    // Vector unary instructions — vs1/vs2 field encodes operation type
    v_VWRXUNARY0 : coverpoint ins.current.insn[19:15] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b010 & ins.current.insn[31:26] == 6'b010000) {
        // VWRXUNARY0: vs1 encodes type, 2^5 bins
    }
    cp_v_VWRXUNARY0: cross priv_mode_m, v_VWRXUNARY0;

    v_VRXUNARY0 : coverpoint ins.current.insn[24:20] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b110 & ins.current.insn[31:26] == 6'b010000) {
        // VRXUNARY0: vs2 encodes type, 2^5 bins (but actually 2^6 with vm bit)
    }
    cp_v_VRXUNARY0: cross priv_mode_m, v_VRXUNARY0;

    v_VXUNARY0 : coverpoint ins.current.insn[19:15] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b010 & ins.current.insn[31:26] == 6'b010010) {
        // VXUNARY0: vs1 encodes type, 2^5 bins
    }
    cp_v_VXUNARY0: cross priv_mode_m, v_VXUNARY0;

    v_VMUNARY0 : coverpoint ins.current.insn[19:15] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b010 & ins.current.insn[31:26] == 6'b010100) {
        // VMUNARY0: vs1 encodes type, 2^5 bins
    }
    cp_v_VMUNARY0: cross priv_mode_m, v_VMUNARY0;

    v_VWFUNARY0 : coverpoint ins.current.insn[19:15] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b001 & ins.current.insn[31:26] == 6'b010000) {
        // VWFUNARY0: vs1 encodes type, 2^5 bins
    }
    cp_v_VWFUNARY0: cross priv_mode_m, v_VWFUNARY0;

    v_VRFUNARY0 : coverpoint ins.current.insn[24:20] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b101 & ins.current.insn[31:26] == 6'b010000) {
        // VRFUNARY0: vs2 encodes type, 2^5 bins (but actually 2^6 with vm bit)
    }
    cp_v_VRFUNARY0: cross priv_mode_m, v_VRFUNARY0;

    v_VFUNARY0 : coverpoint ins.current.insn[19:15] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b001 & ins.current.insn[31:26] == 6'b010010) {
        // VFUNARY0: vs1 encodes type, 2^5 bins
    }
    cp_v_VFUNARY0: cross priv_mode_m, v_VFUNARY0;

    v_VFUNARY1 : coverpoint ins.current.insn[19:15] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b001 & ins.current.insn[31:26] == 6'b010011) {
        // VFUNARY1: vs1 encodes type, 2^5 bins
    }
    cp_v_VFUNARY1: cross priv_mode_m, v_VFUNARY1;

    // Vector crypto — vaes.vv / vaes.vs
    v_vaesvv : coverpoint ins.current.insn[19:15] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b010 & ins.current.insn[31:26] == 6'b101000) {
        // vaes.vv: vs1 encodes type, 2^5 bins
    }
    cp_v_vaesvv: cross priv_mode_m, v_vaesvv;

    v_vaesvs : coverpoint ins.current.insn[19:15] iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b010 & ins.current.insn[31:26] == 6'b101001) {
        // vaes.vs: vs1 encodes type, 2^5 bins
    }
    cp_v_vaesvs: cross priv_mode_m, v_vaesvs;

endgroup

covergroup SsstrictSm_comp_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "priv/RISCV_coverage_comp_instr.svh"

    // main coverpoints
    // Exclude bins matching generator exclusions. The shared RISCV_coverage_comp_instr.svh
    // already has its own ignore_bins; these additional ones match exclusions in
    // SsstrictCommon.py's generate_compressed_instr().

    // compressed00: NO generator exclusions — all encodings are generated.
    // The ignore_bins in RISCV_coverage_comp_instr.svh (c.fld, c.lw, c.lbu, c.lh,
    // c.sb, c.sh, c.fsd, c.sw) are sufficient.
    cp_compressed00: cross priv_mode_m, compressed00;

    cp_compressed01: cross priv_mode_m, compressed01 {
        // "001XXXXXXXXXXX01" — c.jal (RV32) / c.addiw (RV64): already ignored in svh as c_jal
        // "101XXXXXXXXXXX01" — c.j: causes random jump, already ignored in svh as c_j
        // "11XXXXXXXXXXXX01" — c.beqz/c.bnez: causes random branch, already ignored in svh as c_bez_bez
        // "XXXX00010XXXXX01" — rd=x2: clobbers sp (signature pointer), corrupts framework state
        //   insn[15:2] bits[10:6] encode rd; rd=x2 means bits[10:6]=00010
        //   This pattern is scattered across the encoding space, so we use wildcard
        wildcard ignore_bins rd_x2 = binsof(compressed01) intersect {14'b????00010?????};
    }

    cp_compressed10: cross priv_mode_m, compressed10 {
        // "1000XXXXX0000010" — c.jr with rs1!=0: causes random jump, already ignored in svh as c_jr
        // "1001XXXXX0000010" — c.jalr/c.ebreak: causes random jump, already ignored in svh as c_jalr
        // "1001000000000010" — c.ebreak: legal instruction tested elsewhere, already ignored in svh
        // "X01XXXXXXXXXXX10" — c.fldsp/c.fsdsp: interferes with x2/sp (signature pointer), already ignored in svh as c_fldsp/c_fsdsp
        // "X10XXXXXXXXXXX10" — c.lwsp/c.swsp: interferes with x2/sp (signature pointer), already ignored in svh as c_lwsp/c_swsp
        // "XXXX00010XXXXX10" — rd=x2(sp): clobbers signature pointer, corrupts framework state
        wildcard ignore_bins rd_x2 = binsof(compressed10) intersect {14'b????00010?????};
        // "1100XXXXXXXXXX10" — c.swsp with rs2=x2: stores sp value to random address, corrupts signature area
        ignore_bins c_swsp_rs2_x2 = binsof(compressed10) intersect {[14'b11000000000000:14'b11001111111111]};
        // "1110XXXXXXXXXX10" — c.sdsp (RV64) / c.fsw (RV32): interferes with sp-relative memory
        ignore_bins c_sdsp = binsof(compressed10) intersect {[14'b11100000000000:14'b11101111111111]};
        // "1010XXXXXXXXXX10" — nop-like edge in quadrant 2: causes unpredictable behavior on some platforms
        ignore_bins c_nop_edge = binsof(compressed10) intersect {[14'b10100000000000:14'b10101111111111]};
    }
endgroup

function void ssstrictsm_sample(int hart, int issue, ins_t ins);
    SsstrictSm_instr_cg.sample(ins);
    SsstrictSm_comp_instr_cg.sample(ins);
    SsstrictSm_mcsr_cg.sample(ins);

endfunction
