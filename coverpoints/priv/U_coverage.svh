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
    }
    mstatus_FS_off_dirty: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs")[1:0] {
        bins off     = {2'b00};
        bins dirty   = {2'b11};
    }

    // main coverpoints
    cp_fcsr_access:           cross priv_mode_u, fcsrname, csraccesses, mstatus_FS; // superset of ZicsrF cp_fcsr_access crossing with mstatus.FS
    cp_mstatus_FS_transition: cross priv_mode_u, deterministic_instrs, mstatus_FS;
    cp_mstatus_FS_transition_nondeterministic: cross priv_mode_u, nondeterministic_instrs, mstatus_FS_off_dirty;

    // U-mode access to the floating-point CSRs (csraccesses comes from the shared include)
    csrname : coverpoint ins.current.insn[31:20] {
        bins fcsr      = {CSR_FCSR};
        bins fflags    = {CSR_FFLAGS};
        bins frm       = {CSR_FRM};
    }

    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }

    cp_ufcsr_access:           cross priv_mode_u, csrname, csraccesses;
    cp_ufcsrwalk:              cross priv_mode_u, csrname, csrop, walking_ones;
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
    cp_sew_lmul_vsetvl          : cross priv_mode_u, vsetvl_instruction, rs2_vtype_legal, rs2_lmul, rs2_sew;
    cp_sew_lmul_vset_i_vli      : cross priv_mode_u, vset_i_vli_instructions, vset_sew, vset_lmul;
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
    cp_vl_walking1s_sew_lmul    : cross priv_mode_u, vsetivli_prev_instruction, vsetivli_prev_sew_lmul, csrrw, csr_vl, walking_ones_rs1;

    //////////////////////////////////////////////////////////////////////////////////
    // cp_mstatus_vs_*
    // tests mstatus ability to set clean and initial to dirty only when supposed to
    //////////////////////////////////////////////////////////////////////////////////

    mstatus_vs_initial_clean : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins first = {1};
        bins clean  = {2};
    }

    mstatus_vs_inactive    : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins inactive = {0};
    }

    cp_mstatus_vs_set_dirty_arithmetic  : cross priv_mode_u, std_vec,        vector_vector_arithmetic_instruction,   mstatus_vs_initial_clean;
    cp_mstatus_vs_set_dirty_csr         : cross priv_mode_u, std_vec,        vsetvli_instruction,                    mstatus_vs_initial_clean;
    cp_mstatus_vs_set_dirty_vcsr        : cross priv_mode_u, vcsrs_writable, csrops,                                 mstatus_vs_initial_clean;

    // misa is not visible in U-mode, so unlike Sm_V these do not cross misa_v_active
    cp_mstatus_vs_off_arithmetic        : cross priv_mode_u, mstatus_vs_inactive,     vector_vector_arithmetic_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 );
    cp_mstatus_vs_off_csr               : cross priv_mode_u, mstatus_vs_inactive,     vsetvli_instruction iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                                                                                                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 );

    //////////////////////////////////////////////////////////////////////////////////
    // U-mode access to the vector CSRs
    //////////////////////////////////////////////////////////////////////////////////

    csrname : coverpoint ins.current.insn[31:20] {
        bins vstart = {CSR_VSTART};
        bins vxsat  = {CSR_VXSAT};
        bins vxrm   = {CSR_VXRM};
        bins vcsr   = {CSR_VCSR};
        bins vl     = {CSR_VL};
        bins vtype  = {CSR_VTYPE};
        bins vlenb  = {CSR_VLENB};
    }

    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }

    cp_uvcsr_access:           cross priv_mode_u, csrname, csraccesses;
    cp_uvcsrwalk:              cross priv_mode_u, csrname, csrop, walking_ones;
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

    mstatus_fs_initial_clean : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins first_state = {1};
        bins clean  = {2};
    }

    mstatus_fs_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins off = {0};
    }

    cp_vectorfp_mstatus_fs_state_affecting_register : cross priv_mode_u, std_vec, vfmv_f_s, mstatus_fs_initial_clean;
    cp_vectorfp_mstatus_fs_state_affecting_csr      : cross priv_mode_u, std_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_initial_clean, fflags_modified_after_clear;
    cp_vectorfp_mstatus_fs_state_nonaffecting       : cross priv_mode_u, std_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_initial_clean, vs1_zero, vs2_zero;
    cp_vectorfp_mstatus_fs_off                      : cross priv_mode_u, std_trap_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_off, vs1_zero, vs2_zero;

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
endfunction
