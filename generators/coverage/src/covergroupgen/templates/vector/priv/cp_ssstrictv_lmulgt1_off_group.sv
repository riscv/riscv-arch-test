// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_lmulgt1_off_group
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // LMUL=2: vd, vs1, vs2 not divisible by 2 should trap
    cp_ssstrictv_lmul2_vd_off_group: cross std_trap_vec, vtype_lmul_2, vd_all_reg_unaligned_lmul_2;
    cp_ssstrictv_lmul2_vs1_off_group: cross std_trap_vec, vtype_lmul_2, vs1_all_reg_unaligned_lmul_2;
    cp_ssstrictv_lmul2_vs2_off_group: cross std_trap_vec, vtype_lmul_2, vs2_all_reg_unaligned_lmul_2;

    // LMUL=4: vd, vs1, vs2 not divisible by 4 should trap
    cp_ssstrictv_lmul4_vd_off_group: cross std_trap_vec, vtype_lmul_4, vd_all_reg_unaligned_lmul_4;
    cp_ssstrictv_lmul4_vs1_off_group: cross std_trap_vec, vtype_lmul_4, vs1_all_reg_unaligned_lmul_4;
    cp_ssstrictv_lmul4_vs2_off_group: cross std_trap_vec, vtype_lmul_4, vs2_all_reg_unaligned_lmul_4;

    // LMUL=8: vd, vs1, vs2 not divisible by 8 should trap
    cp_ssstrictv_lmul8_vd_off_group: cross std_trap_vec, vtype_lmul_8, vd_all_reg_unaligned_lmul_8;
    cp_ssstrictv_lmul8_vs1_off_group: cross std_trap_vec, vtype_lmul_8, vs1_all_reg_unaligned_lmul_8;
    cp_ssstrictv_lmul8_vs2_off_group: cross std_trap_vec, vtype_lmul_8, vs2_all_reg_unaligned_lmul_8;

//// end cp_ssstrictv_lmulgt1_off_group ///////////////////////////////////////////////////////////
