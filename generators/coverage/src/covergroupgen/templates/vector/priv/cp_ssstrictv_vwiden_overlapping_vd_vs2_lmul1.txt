// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Widening with LMUL=1: vs2 = vd overlaps destination group, must trap
    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1: cross std_trap_vec, vtype_lmul_1, vd_reg_aligned_lmul_2, vd_eq_vs2, vs1_vd_no_overlap_lmul1, trap_occurred;

//// end cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1 /////////////////////////////////////////////////////////
