// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vrgather_vd_vs1_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vrgather.vv: destination register group cannot overlap vs1 register group
    cp_ssstrictv_vrgather_vd_vs1_overlap_lmul1: cross std_trap_vec, vtype_lmul_1, vd_eq_vs1;

    cp_ssstrictv_vrgather_vd_vs1_overlap_lmul2: cross std_trap_vec, vtype_lmul_2, vs1_vd_overlap_lmul1;

    cp_ssstrictv_vrgather_vd_vs1_overlap_lmul4: cross std_trap_vec, vtype_lmul_4, vs1_vd_overlap_lmul2;

    cp_ssstrictv_vrgather_vd_vs1_overlap_lmul8: cross std_trap_vec, vtype_lmul_8, vs1_vd_overlap_lmul4;

//// end cp_ssstrictv_vrgather_vd_vs1_overlap ///////////////////////////////////////////////////////////////
