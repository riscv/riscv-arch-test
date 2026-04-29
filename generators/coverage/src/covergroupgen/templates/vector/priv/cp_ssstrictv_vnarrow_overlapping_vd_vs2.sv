// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vnarrow_overlapping_vd_vs2
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Narrowing with LMUL=1: vd = vs2 overlaps source group, must trap
    trap_occurred_eb4360: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == 2) {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vnarrow_overlapping_vd_vs2: cross std_trap_vec, vtype_lmul_1, vs2_reg_aligned_lmul_2, vd_eq_vs2, trap_occurred_eb4360;

//// end cp_ssstrictv_vnarrow_overlapping_vd_vs2 /////////////////////////////////////////////////////////
