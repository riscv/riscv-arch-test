// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vwidenw_overlapping_vd_vs1_lmul1
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Widening .w with LMUL=1: vs1 = vd overlaps low part of destination group, must trap
    trap_occurred_71b3d0: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == 2) {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vwidenw_overlapping_vd_vs1_lmul1: cross std_trap_vec, vtype_lmul_1, vd_reg_aligned_lmul_2, vd_eq_vs1, vs2_vd_no_overlap_lmul1, trap_occurred_71b3d0;

//// end cp_ssstrictv_vwidenw_overlapping_vd_vs1_lmul1 /////////////////////////////////////////////////////////
