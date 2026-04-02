// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vext2_overlapping_vd_vs2
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vf2 widening with LMUL=2: vs2 overlaps bottom half of vd group (vs2 == vd), must trap
    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vext2_overlapping_vd_vs2: cross std_trap_vec, vtype_lmul_2, vd_eq_vs2, trap_occurred;

//// end cp_ssstrictv_vext2_overlapping_vd_vs2 ///////////////////////////////////////////////////////////////
