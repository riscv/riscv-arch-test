// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vext8_overlapping_vd_vs2
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vf8 extending with LMUL=8: vs2 overlaps bottom 7/8 of vd group, must trap
    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    // vs2 is not the highest register in the 8-register vd group (offset != 7)
    vs2_not_top_of_group_8: coverpoint ins.current.insn[22:20] {
        bins bottom = {[3'b000:3'b110]};
    }

    cp_ssstrictv_vext8_overlapping_vd_vs2: cross std_trap_vec, vtype_lmul_8, vd_reg_aligned_lmul_8, vs2_vd_overlap_lmul4, vs2_not_top_of_group_8, trap_occurred;

//// end cp_ssstrictv_vext8_overlapping_vd_vs2 ///////////////////////////////////////////////////////////////
