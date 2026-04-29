// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Widening with LMUL=1: vs2 = vd overlaps destination group, must trap
    trap_occurred_5c5a36: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == 2) {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1: cross std_trap_vec, vtype_lmul_1, vd_reg_aligned_lmul_2, vd_eq_vs2, vs1_vd_no_overlap_lmul1, trap_occurred_5c5a36;

//// end cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1 /////////////////////////////////////////////////////////
