// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcompress_vd_vs2_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vcompress: destination register group cannot overlap source register group (vs2)
    cp_ssstrictv_vcompress_vd_vs2_overlap_lmul1: cross std_trap_vec, vtype_lmul_1, vd_eq_vs2;

    cp_ssstrictv_vcompress_vd_vs2_overlap_lmul2: cross std_trap_vec, vtype_lmul_2, vs2_vd_overlap_lmul1;

    cp_ssstrictv_vcompress_vd_vs2_overlap_lmul4: cross std_trap_vec, vtype_lmul_4, vs2_vd_overlap_lmul2;

    cp_ssstrictv_vcompress_vd_vs2_overlap_lmul8: cross std_trap_vec, vtype_lmul_8, vs2_vd_overlap_lmul4;

//// end cp_ssstrictv_vcompress_vd_vs2_overlap ///////////////////////////////////////////////////////////////
