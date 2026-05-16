// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vext4_overlapping_vd_vs2
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vf4 extending with LMUL=4: vs2 overlaps bottom 3/4 of vd group, must trap
    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    // vs2 is not the highest register in the 4-register vd group (offset != 3)
    vs2_not_top_of_group_4: coverpoint ins.current.insn[21:20] {
        bins bottom = {[2'b00:2'b10]};
    }

    cp_ssstrictv_vext4_overlapping_vd_vs2: cross std_trap_vec, vtype_lmul_4, vd_reg_aligned_lmul_4, vs2_vd_overlap_lmul2, vs2_not_top_of_group_4, trap_occurred;

//// end cp_ssstrictv_vext4_overlapping_vd_vs2 ///////////////////////////////////////////////////////////////
