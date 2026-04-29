// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vext2_overlapping_vd_vs2
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vf2 widening with LMUL=2: vs2 overlaps bottom half of vd group (vs2 == vd), must trap
    trap_occurred_7e859f: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == 2) {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vext2_overlapping_vd_vs2: cross std_trap_vec, vtype_lmul_2, vd_eq_vs2, trap_occurred_7e859f;

//// end cp_ssstrictv_vext2_overlapping_vd_vs2 ///////////////////////////////////////////////////////////////
