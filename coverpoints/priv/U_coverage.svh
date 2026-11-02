///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 13 November 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_U
covergroup U_uprivinst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    privinstrs: coverpoint ins.current.insn  {
        bins ecall  = {ECALL};
        bins ebreak = {EBREAK};
        bins mret   = {MRET};
        bins sret   = {SRET};
    }
    // main coverpoints
    cp_uprivinst:  cross priv_mode_u, privinstrs;
endgroup

covergroup U_ucsr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csr_nonuser: coverpoint ins.current.insn[31:20]  {
        bins nonuser_0[] = {[12'h100:12'h3FF]};
        bins nonuser_1[] = {[12'h500:12'h7FF]};
        bins nonuser_2[] = {[12'h900:12'hBFF]};
        bins nonuser_3[] = {[12'hD00:12'hFFF]};
    }
    csrr: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
    }
    csrw: coverpoint ins.current.insn  {
        wildcard bins csrw = {CSRRW};
    }
    csr_uro: coverpoint ins.current.insn[31:20]  {
        bins sro[] = {[12'hC00:12'hCFF]};
    }
    nonzerord: coverpoint ins.current.insn[11:7] {
        type_option.weight = 0;
        bins nonzero = { [1:$] }; // rd != 0
    }

    cp_csr_insufficient_priv: cross priv_mode_u, csrr, csr_nonuser, nonzerord;
    cp_csr_ro:                cross priv_mode_u, csrw, csr_uro;
endgroup


// U_F, U_V and U_VF tests (U_F-NN.S, U_V_*-NN.S, U_VF-NN.S) are part of the U suite and run only
// when F, Zve32x or Zve32f is also supported. They parallel Sm_F, Sm_V and Sm_VF in Sm_coverage.svh,
// reaching sstatus (or mstatus without S-mode) through T-SBI, and share their coverpoints through the
// general/RISCV_coverage_priv_* includes.
`ifdef F_SUPPORTED
covergroup U_F_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_f_coverpoints.svh"

    mstatus_FS: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs")[1:0] {
        bins off     = {2'b00};
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins initial_state = {2'b01};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean   = {2'b10};
        `endif
        bins dirty   = {2'b11};
    }
    mstatus_FS_off_dirty: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs")[1:0] {
        bins off     = {2'b00};
        bins dirty   = {2'b11};
    }

    // main coverpoints
    cp_fcsr_access:           cross priv_mode_u, fcsrname, csraccesses, mstatus_FS; // superset of ZicsrF cp_fcsr_access crossing with mstatus.FS
    cp_mstatus_FS_transition: cross priv_mode_u, deterministic_instrs, mstatus_FS;
    cp_mstatus_FS_transition_nondeterministic: cross priv_mode_u, nondeterministic_instrs, mstatus_FS_off_dirty;
endgroup
`endif

`ifdef ZVE32X_SUPPORTED
covergroup U_V_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_v_coverpoints.svh"

    // crosses of the shared vector coverpoints
    cp_vcsrrswc                 : cross priv_mode_u, vcsrs, csrops;
    cp_vcsrs_walking1s          : cross priv_mode_u, writable_vcsrs, csrw, walking_ones_rs1;
    cp_sew_lmul_vsetvl          : cross priv_mode_u, vsetvl_instruction, rs2_vtype_legal, rs2_lmul, rs2_sew {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            ignore_bins illegal_sew_lmul =
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b111 }) ||  // SEW = 64, LMUL = f2
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 64, LMUL = f4
                (binsof(rs2_sew) intersect { 3'b011 } && binsof(rs2_lmul) intersect { 3'b101 }) ||  // SEW = 64, LMUL = f8
                (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 32, LMUL = f4
                (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b101 }) ||  // SEW = 32, LMUL = f8
                (binsof(rs2_sew) intersect { 3'b001 } && binsof(rs2_lmul) intersect { 3'b101 });    // SEW = 16, LMUL = f8

            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 =
                    (binsof(rs2_sew) intersect { 3'b010 } && binsof(rs2_lmul) intersect { 3'b111 }) ||  // SEW = 32, LMUL = f2
                    (binsof(rs2_sew) intersect { 3'b001 } && binsof(rs2_lmul) intersect { 3'b110 }) ||  // SEW = 16, LMUL = f4
                    (binsof(rs2_sew) intersect { 3'b000 } && binsof(rs2_lmul) intersect { 3'b101 });    // SEW = 8, LMUL = f8
            `endif
        `endif
    }
    cp_sew_lmul_vset_i_vli      : cross priv_mode_u, vset_i_vli_instructions, vset_sew, vset_lmul {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            ignore_bins illegal_sew_lmul =
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b111 }) ||  // SEW = 64, LMUL = f2
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 64, LMUL = f4
                (binsof(vset_sew) intersect { 3'b011 } && binsof(vset_lmul) intersect { 3'b101 }) ||  // SEW = 64, LMUL = f8
                (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 32, LMUL = f4
                (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b101 }) ||  // SEW = 32, LMUL = f8
                (binsof(vset_sew) intersect { 3'b001 } && binsof(vset_lmul) intersect { 3'b101 });    // SEW = 16, LMUL = f8

            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 =
                    (binsof(vset_sew) intersect { 3'b010 } && binsof(vset_lmul) intersect { 3'b111 }) ||  // SEW = 32, LMUL = f2
                    (binsof(vset_sew) intersect { 3'b001 } && binsof(vset_lmul) intersect { 3'b110 }) ||  // SEW = 16, LMUL = f4
                    (binsof(vset_sew) intersect { 3'b000 } && binsof(vset_lmul) intersect { 3'b101 });    // SEW = 8, LMUL = f8
            `endif
        `endif
    }
    cp_vill_vsetvl              : cross priv_mode_u, vsetvl_instruction, vtype_prev_vill_set, rs2_vtype_legal, rs2_sew_all_supported, rs2_lmul_8;
    cp_vill_vset_i_vli          : cross priv_mode_u, vset_i_vli_instructions, vtype_prev_vill_set, current_vset_sew_all_supported, current_vset_lmul_8;
    cp_vill_vsetvl_rs2_vill     : cross priv_mode_u, vsetvl_instruction, vtype_prev_vill_set, rs2_vtype_legal_no_msb, rs2_sew_all_supported, rs2_lmul_8, rs2_vill_set;
    cp_vsetvl_rs2_vill          : cross priv_mode_u, vsetvl_instruction, rs2_vill_set, rs2_sew_supported, rs2_lmul_1, rs2_vtype_legal_no_msb, vtype_prev_vill_clear;
    cp_vtype_vill_set_vl_0      : cross priv_mode_u, vsetvl_instruction, rs1_non_zero, rs2_vill_set, vl_nonzero;
    cp_vsetvl_i_rd_nx0_rs1_x0   : cross priv_mode_u, vsetvl_i_instructions, vl_not_max, rd_n0, rs1_x0, vtype_all_sew_supported, vtype_all_lmul_supported {
        // SEW > LMUL*ELEN sets vill=1 and forces vtype.vsew/vlmul to 0,
        // so these BEFORE-state (sew, lmul) pairs are architecturally unreachable.
        ignore_bins illegal_sew_lmul =
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.half))   ||
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.fourth)) ||
            (binsof(vtype_all_sew_supported.sixtyfour) && binsof(vtype_all_lmul_supported.eighth)) ||
            (binsof(vtype_all_sew_supported.thirtytwo) && binsof(vtype_all_lmul_supported.fourth)) ||
            (binsof(vtype_all_sew_supported.thirtytwo) && binsof(vtype_all_lmul_supported.eighth)) ||
            (binsof(vtype_all_sew_supported.sixteen)   && binsof(vtype_all_lmul_supported.eighth));
    }
    cp_vsetvl_i_rd_x0_rs1_x0    : cross priv_mode_u, vsetvl_i_instructions, vl_nonzero, rd_x0, rs1_x0, vset_i_vli_vlmax_unchanged;
    cp_vsetvl_i_avl_eq_zero     : cross priv_mode_u, vsetvl_i_instructions, rs1_eq_zero;
    cp_vsetvl_i_avl_eq_vlmax    : cross priv_mode_u, vsetvl_i_instructions, rs1_eq_vlmax;
    cp_vsetvl_i_avl_lt_2x_vlmax : cross priv_mode_u, vsetvl_i_instructions, rs1_lt_2x_vlmax_gt_vlmax;
    cp_vsetvl_i_avl_eq_2x_vlmax : cross priv_mode_u, vsetvl_i_instructions, rs1_eq_2x_vlmax;
    cp_vsetvl_i_avl_gt_2x_vlmax : cross priv_mode_u, vsetvl_i_instructions, rs1_gt_2x_vlmax;
    cp_vsetivli_avl_edges       : cross priv_mode_u, vsetivli_instruction, vtype_all_sew_supported, imm5_edges, vtype_lmul_1;
    cp_vstart_out_of_bounds     : cross priv_mode_u, vstart_csr, csr_write, rs1_2_to_16;
    cp_vl_walking1s_sew_lmul    : cross priv_mode_u, vsetivli_prev_instruction, vsetivli_prev_sew_lmul, csrrw, csr_vl, walking_ones_rs1 {
        `ifndef UDB_SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED_NO_UNREQUIRED_SUPPORTED
            // SEW > LMUL*ELEN sets vill; the tests skip these unless the DUT supports the extra fractional LMULs.
            // Encodings are {vsew, vlmul}. ELEN is at most 64, so ELEN>=128 pairs are never legal.
            ignore_bins illegal_sew_lmul = binsof(vsetivli_prev_sew_lmul) intersect {
                5'b01_101,  // e16, mf8
                5'b10_110,  // e32, mf4
                5'b10_101,  // e32, mf8
                5'b11_111,  // e64, mf2
                5'b11_110,  // e64, mf4
                5'b11_101   // e64, mf8
            };
            `ifndef UDB_ELEN_64
                ignore_bins illegal_sew_lmul_elen32 = binsof(vsetivli_prev_sew_lmul) intersect {
                    5'b00_101,  // e8, mf8
                    5'b01_110,  // e16, mf4
                    5'b10_111   // e32, mf2
                };
            `endif
        `endif
    }

    //////////////////////////////////////////////////////////////////////////////////
    // cp_mstatus_vs_*
    // tests mstatus ability to set clean and initial to dirty only when supposed to
    //////////////////////////////////////////////////////////////////////////////////

    // Initial and Clean only when MSTATUS_VS_LEGAL_VALUES includes them (otherwise a write
    // of either reads back as Dirty)
    mstatus_vs_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_1
            bins first = {1};
        `endif
        `ifdef UDB_MSTATUS_VS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }

    mstatus_vs_inactive    : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins inactive = {0};
    }

    cp_mstatus_vs_set_dirty_arithmetic  : cross priv_mode_u, std_vec,        vector_vector_arithmetic_instruction,   mstatus_vs_on;
    cp_mstatus_vs_set_dirty_csr         : cross priv_mode_u, std_vec,        vsetvli_instruction,                    mstatus_vs_on;
    cp_mstatus_vs_set_dirty_vcsr        : cross priv_mode_u, vcsrs_writable, csrops,                                 mstatus_vs_on;

    cp_mstatus_vs_off_arithmetic        : cross priv_mode_u, mstatus_vs_inactive,     vector_vector_arithmetic_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 );
    cp_mstatus_vs_off_csr               : cross priv_mode_u, mstatus_vs_inactive,     vsetvli_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 );
endgroup
`endif

`ifdef ZVE32F_SUPPORTED
covergroup U_VF_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_priv_vf_coverpoints.svh"

    //cross vtype_prev_vill_clear, vstart_zero, vl_nonzero;
    std_trap_vec : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    // Initial and Clean only when MSTATUS_FS_LEGAL_VALUES includes them (otherwise a write
    // of either reads back as Dirty)
    mstatus_fs_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_1
            bins first_state = {1};
        `endif
        `ifdef UDB_MSTATUS_FS_LEGAL_VALUES_2
            bins clean  = {2};
        `endif
        bins dirty  = {3};
    }

    mstatus_fs_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins off = {0};
    }

    cp_vectorfp_mstatus_fs_state_affecting_register : cross priv_mode_u, std_vec, vfmv_f_s, mstatus_fs_on;
    cp_vectorfp_mstatus_fs_state_affecting_csr      : cross priv_mode_u, std_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_on, fflags_modified_after_clear;
    cp_vectorfp_mstatus_fs_state_nonaffecting       : cross priv_mode_u, std_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_on, vs1_zero, vs2_zero;
    cp_vectorfp_mstatus_fs_off                      : cross priv_mode_u, std_trap_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_off, vs1_zero, vs2_zero;

endgroup
`endif

`ifdef ZICNTR_SUPPORTED
covergroup U_Zicntr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // Counter access in user mode

    // building blocks for the main coverpoints
    csraccess: coverpoint ins.current.insn  {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
    }
    mcounteren_zeros: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren"){
        bins zeros = {32'b0};
    }

    counters_mcounteren: coverpoint {ins.current.insn[31:20], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcounteren", "mcounteren")[31:0] } {
        bins cycle_enabled         = {44'b110000000000_00000000000000000000000000000001};
        bins time_enabled          = {44'b110000000001_00000000000000000000000000000010};
        bins instret_enabled       = {44'b110000000010_00000000000000000000000000000100};
        `ifdef ZIHPM_SUPPORTED
          `ifdef UDB_HPM_COUNTER_EN_3
            bins hpmcounter3_enabled   = {44'b110000000011_00000000000000000000000000001000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_4
            bins hpmcounter4_enabled   = {44'b110000000100_00000000000000000000000000010000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_5
            bins hpmcounter5_enabled   = {44'b110000000101_00000000000000000000000000100000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_6
            bins hpmcounter6_enabled   = {44'b110000000110_00000000000000000000000001000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_7
            bins hpmcounter7_enabled   = {44'b110000000111_00000000000000000000000010000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_8
            bins hpmcounter8_enabled   = {44'b110000001000_00000000000000000000000100000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_9
            bins hpmcounter9_enabled   = {44'b110000001001_00000000000000000000001000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_10
            bins hpmcounter10_enabled  = {44'b110000001010_00000000000000000000010000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_11
            bins hpmcounter11_enabled  = {44'b110000001011_00000000000000000000100000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_12
            bins hpmcounter12_enabled  = {44'b110000001100_00000000000000000001000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_13
            bins hpmcounter13_enabled  = {44'b110000001101_00000000000000000010000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_14
            bins hpmcounter14_enabled  = {44'b110000001110_00000000000000000100000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_15
            bins hpmcounter15_enabled  = {44'b110000001111_00000000000000001000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_16
            bins hpmcounter16_enabled  = {44'b110000010000_00000000000000010000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_17
            bins hpmcounter17_enabled  = {44'b110000010001_00000000000000100000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_18
            bins hpmcounter18_enabled  = {44'b110000010010_00000000000001000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_19
            bins hpmcounter19_enabled  = {44'b110000010011_00000000000010000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_20
            bins hpmcounter20_enabled  = {44'b110000010100_00000000000100000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_21
            bins hpmcounter21_enabled  = {44'b110000010101_00000000001000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_22
            bins hpmcounter22_enabled  = {44'b110000010110_00000000010000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_23
            bins hpmcounter23_enabled  = {44'b110000010111_00000000100000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_24
            bins hpmcounter24_enabled  = {44'b110000011000_00000001000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_25
            bins hpmcounter25_enabled  = {44'b110000011001_00000010000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_26
            bins hpmcounter26_enabled  = {44'b110000011010_00000100000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_27
            bins hpmcounter27_enabled  = {44'b110000011011_00001000000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_28
            bins hpmcounter28_enabled  = {44'b110000011100_00010000000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_29
            bins hpmcounter29_enabled  = {44'b110000011101_00100000000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_30
            bins hpmcounter30_enabled  = {44'b110000011110_01000000000000000000000000000000};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_31
            bins hpmcounter31_enabled  = {44'b110000011111_10000000000000000000000000000000};
          `endif
        `endif

        bins cycle_disabled         = {44'b110000000000_11111111111111111111111111111110};
        bins time_disabled          = {44'b110000000001_11111111111111111111111111111101};
        bins instret_disabled       = {44'b110000000010_11111111111111111111111111111011};
        `ifdef ZIHPM_SUPPORTED
          `ifdef UDB_HPM_COUNTER_EN_3
            bins hpmcounter3_disabled   = {44'b110000000011_11111111111111111111111111110111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_4
            bins hpmcounter4_disabled   = {44'b110000000100_11111111111111111111111111101111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_5
            bins hpmcounter5_disabled   = {44'b110000000101_11111111111111111111111111011111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_6
            bins hpmcounter6_disabled   = {44'b110000000110_11111111111111111111111110111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_7
            bins hpmcounter7_disabled   = {44'b110000000111_11111111111111111111111101111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_8
            bins hpmcounter8_disabled   = {44'b110000001000_11111111111111111111111011111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_9
            bins hpmcounter9_disabled   = {44'b110000001001_11111111111111111111110111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_10
            bins hpmcounter10_disabled  = {44'b110000001010_11111111111111111111101111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_11
            bins hpmcounter11_disabled  = {44'b110000001011_11111111111111111111011111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_12
            bins hpmcounter12_disabled  = {44'b110000001100_11111111111111111110111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_13
            bins hpmcounter13_disabled  = {44'b110000001101_11111111111111111101111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_14
            bins hpmcounter14_disabled  = {44'b110000001110_11111111111111111011111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_15
            bins hpmcounter15_disabled  = {44'b110000001111_11111111111111110111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_16
            bins hpmcounter16_disabled  = {44'b110000010000_11111111111111101111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_17
            bins hpmcounter17_disabled  = {44'b110000010001_11111111111111011111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_18
            bins hpmcounter18_disabled  = {44'b110000010010_11111111111110111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_19
            bins hpmcounter19_disabled  = {44'b110000010011_11111111111101111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_20
            bins hpmcounter20_disabled  = {44'b110000010100_11111111111011111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_21
            bins hpmcounter21_disabled  = {44'b110000010101_11111111110111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_22
            bins hpmcounter22_disabled  = {44'b110000010110_11111111101111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_23
            bins hpmcounter23_disabled  = {44'b110000010111_11111111011111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_24
            bins hpmcounter24_disabled  = {44'b110000011000_11111110111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_25
            bins hpmcounter25_disabled  = {44'b110000011001_11111101111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_26
            bins hpmcounter26_disabled  = {44'b110000011010_11111011111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_27
            bins hpmcounter27_disabled  = {44'b110000011011_11110111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_28
            bins hpmcounter28_disabled  = {44'b110000011100_11101111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_29
            bins hpmcounter29_disabled  = {44'b110000011101_11011111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_30
            bins hpmcounter30_disabled  = {44'b110000011110_10111111111111111111111111111111};
          `endif
          `ifdef UDB_HPM_COUNTER_EN_31
            bins hpmcounter31_disabled  = {44'b110000011111_01111111111111111111111111111111};
          `endif
        `endif

        `ifdef UDB_MXLEN_32
            bins cycleh_enabled         = {44'b110010000000_00000000000000000000000000000001};
            bins timeh_enabled          = {44'b110010000001_00000000000000000000000000000010};
            bins instreth_enabled       = {44'b110010000010_00000000000000000000000000000100};
            `ifdef ZIHPM_SUPPORTED
              `ifdef UDB_HPM_COUNTER_EN_3
                bins hpmcounter3h_enabled   = {44'b110010000011_00000000000000000000000000001000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_4
                bins hpmcounter4h_enabled   = {44'b110010000100_00000000000000000000000000010000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_5
                bins hpmcounter5h_enabled   = {44'b110010000101_00000000000000000000000000100000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_6
                bins hpmcounter6h_enabled   = {44'b110010000110_00000000000000000000000001000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_7
                bins hpmcounter7h_enabled   = {44'b110010000111_00000000000000000000000010000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_8
                bins hpmcounter8h_enabled   = {44'b110010001000_00000000000000000000000100000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_9
                bins hpmcounter9h_enabled   = {44'b110010001001_00000000000000000000001000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_10
                bins hpmcounter10h_enabled  = {44'b110010001010_00000000000000000000010000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_11
                bins hpmcounter11h_enabled  = {44'b110010001011_00000000000000000000100000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_12
                bins hpmcounter12h_enabled  = {44'b110010001100_00000000000000000001000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_13
                bins hpmcounter13h_enabled  = {44'b110010001101_00000000000000000010000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_14
                bins hpmcounter14h_enabled  = {44'b110010001110_00000000000000000100000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_15
                bins hpmcounter15h_enabled  = {44'b110010001111_00000000000000001000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_16
                bins hpmcounter16h_enabled  = {44'b110010010000_00000000000000010000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_17
                bins hpmcounter17h_enabled  = {44'b110010010001_00000000000000100000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_18
                bins hpmcounter18h_enabled  = {44'b110010010010_00000000000001000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_19
                bins hpmcounter19h_enabled  = {44'b110010010011_00000000000010000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_20
                bins hpmcounter20h_enabled  = {44'b110010010100_00000000000100000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_21
                bins hpmcounter21h_enabled  = {44'b110010010101_00000000001000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_22
                bins hpmcounter22h_enabled  = {44'b110010010110_00000000010000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_23
                bins hpmcounter23h_enabled  = {44'b110010010111_00000000100000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_24
                bins hpmcounter24h_enabled  = {44'b110010011000_00000001000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_25
                bins hpmcounter25h_enabled  = {44'b110010011001_00000010000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_26
                bins hpmcounter26h_enabled  = {44'b110010011010_00000100000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_27
                bins hpmcounter27h_enabled  = {44'b110010011011_00001000000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_28
                bins hpmcounter28h_enabled  = {44'b110010011100_00010000000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_29
                bins hpmcounter29h_enabled  = {44'b110010011101_00100000000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_30
                bins hpmcounter30h_enabled  = {44'b110010011110_01000000000000000000000000000000};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_31
                bins hpmcounter31h_enabled  = {44'b110010011111_10000000000000000000000000000000};
              `endif
            `endif

            bins cycleh_disabled         = {44'b110010000000_11111111111111111111111111111110};
            bins timeh_disabled          = {44'b110010000001_11111111111111111111111111111101};
            bins instreth_disabled       = {44'b110010000010_11111111111111111111111111111011};
            `ifdef ZIHPM_SUPPORTED
              `ifdef UDB_HPM_COUNTER_EN_3
                bins hpmcounter3h_disabled   = {44'b110010000011_11111111111111111111111111110111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_4
                bins hpmcounter4h_disabled   = {44'b110010000100_11111111111111111111111111101111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_5
                bins hpmcounter5h_disabled   = {44'b110010000101_11111111111111111111111111011111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_6
                bins hpmcounter6h_disabled   = {44'b110010000110_11111111111111111111111110111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_7
                bins hpmcounter7h_disabled   = {44'b110010000111_11111111111111111111111101111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_8
                bins hpmcounter8h_disabled   = {44'b110010001000_11111111111111111111111011111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_9
                bins hpmcounter9h_disabled   = {44'b110010001001_11111111111111111111110111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_10
                bins hpmcounter10h_disabled  = {44'b110010001010_11111111111111111111101111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_11
                bins hpmcounter11h_disabled  = {44'b110010001011_11111111111111111111011111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_12
                bins hpmcounter12h_disabled  = {44'b110010001100_11111111111111111110111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_13
                bins hpmcounter13h_disabled  = {44'b110010001101_11111111111111111101111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_14
                bins hpmcounter14h_disabled  = {44'b110010001110_11111111111111111011111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_15
                bins hpmcounter15h_disabled  = {44'b110010001111_11111111111111110111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_16
                bins hpmcounter16h_disabled  = {44'b110010010000_11111111111111101111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_17
                bins hpmcounter17h_disabled  = {44'b110010010001_11111111111111011111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_18
                bins hpmcounter18h_disabled  = {44'b110010010010_11111111111110111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_19
                bins hpmcounter19h_disabled  = {44'b110010010011_11111111111101111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_20
                bins hpmcounter20h_disabled  = {44'b110010010100_11111111111011111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_21
                bins hpmcounter21h_disabled  = {44'b110010010101_11111111110111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_22
                bins hpmcounter22h_disabled  = {44'b110010010110_11111111101111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_23
                bins hpmcounter23h_disabled  = {44'b110010010111_11111111011111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_24
                bins hpmcounter24h_disabled  = {44'b110010011000_11111110111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_25
                bins hpmcounter25h_disabled  = {44'b110010011001_11111101111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_26
                bins hpmcounter26h_disabled  = {44'b110010011010_11111011111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_27
                bins hpmcounter27h_disabled  = {44'b110010011011_11110111111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_28
                bins hpmcounter28h_disabled  = {44'b110010011100_11101111111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_29
                bins hpmcounter29h_disabled  = {44'b110010011101_11011111111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_30
                bins hpmcounter30h_disabled  = {44'b110010011110_10111111111111111111111111111111};
              `endif
              `ifdef UDB_HPM_COUNTER_EN_31
                bins hpmcounter31h_disabled  = {44'b110010011111_01111111111111111111111111111111};
              `endif
            `endif
        `endif
    }

    // main coverpoints
    cp_mcounteren_access_u: cross csraccess, counters_mcounteren, priv_mode_u;
    cp_mcounter_inc_inaccessible: cross mcounteren_zeros, priv_mode_u;

    // ---- instret delta coverpoints ----

    ecall: coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    ebreak: coverpoint ins.current.insn {
        bins ebreak = {EBREAK};
    }
    insn_lw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    adr_misaligned_1: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] {
        bins one = {3'b001};  // scratch + 1
    }
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
    `endif
    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }
    mie_mtie_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mtie")[0] {
        bins one = {1};
    }

    insn_add_u: coverpoint ins.current.insn {
        wildcard bins add = {ADD};
    }
    `ifdef ZAWRS_SUPPORTED
        wrs_nto: coverpoint ins.current.insn {
            bins wrs_nto = {WRS_NTO};
        }
        wrs_sto: coverpoint ins.current.insn {
            bins wrs_sto = {WRS_STO};
        }
    `endif

    prev_instret_read: coverpoint ins.prev.insn {
        wildcard bins csrr_instret = {32'b110000000010_00000_010_?????_1110011};  // csrr rd, instret (0xC02)
    }
    prev_ecall_li: coverpoint ins.prev.insn {
        bins li_a0 = {32'h07300513};  // addi a0, x0, 0x73 (RVTEST_TSBI_ECALL_TEST)
    }
    mie_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mie", "mie")[31:0] {
        bins zero = {0};
    }

    // retiring instruction
    cp_instret_add: cross priv_mode_u, insn_add_u, prev_instret_read;

    // instructions that trap before retiring
    cp_instret_ecall:  cross priv_mode_u, ecall, prev_ecall_li;
    cp_instret_ebreak: cross priv_mode_u, ebreak, prev_instret_read;
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        cp_instret_load_access_fault: cross priv_mode_u, insn_lw, illegal_address, prev_instret_read;
    `endif
    cp_instret_load_misaligned: cross priv_mode_u, insn_lw, adr_misaligned_1, prev_instret_read;

    // wfi and wrs
    `ifdef UDB_WFI_FINITE
        `ifdef UDB_WFI_U_MODE
            cp_instret_wfi_timeout: cross priv_mode_u, wfi, mie_zero, prev_instret_read;
        `endif
    `endif
    `ifdef UDB_WFI_U_MODE
        `ifdef UDB_MTI_INTR_IMPL
            cp_instret_wfi_taken: cross priv_mode_u, wfi, mie_mtie_one;
        `endif
    `endif
    `ifdef ZAWRS_SUPPORTED
        cp_instret_wrs_nto: cross priv_mode_u, wrs_nto, prev_instret_read;
        cp_instret_wrs_sto: cross priv_mode_u, wrs_sto, prev_instret_read;
    `endif

endgroup
`endif

function void u_sample(int hart, int issue, ins_t ins);
    U_uprivinst_cg.sample(ins);
    U_ucsr_cg.sample(ins);
    `ifdef F_SUPPORTED
        U_F_cg.sample(ins);
    `endif
    `ifdef ZVE32X_SUPPORTED
        U_V_cg.sample(ins);
    `endif
    `ifdef ZVE32F_SUPPORTED
        U_VF_cg.sample(ins);
    `endif
    `ifdef ZICNTR_SUPPORTED
        U_Zicntr_cg.sample(ins);
    `endif
endfunction
