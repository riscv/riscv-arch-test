// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcompress_vd_v0_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vcompress: destination register group cannot overlap source mask register (v0)
    cp_ssstrictv_vcompress_vd_v0_overlap_lmul1: cross std_trap_vec, vtype_lmul_1, vd_v0;

    cp_ssstrictv_vcompress_vd_v0_overlap_lmul2: cross std_trap_vec, vtype_lmul_2, vd_v0;

    cp_ssstrictv_vcompress_vd_v0_overlap_lmul4: cross std_trap_vec, vtype_lmul_4, vd_v0;

    cp_ssstrictv_vcompress_vd_v0_overlap_lmul8: cross std_trap_vec, vtype_lmul_8, vd_v0;

//// end cp_ssstrictv_vcompress_vd_v0_overlap ///////////////////////////////////////////////////////////////
