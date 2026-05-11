// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_narrowing_vs2_sew_eq_elen
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Narrowing with SEW=ELEN: source EEW = 2*SEW > ELEN, must trap
    // LMUL=1, registers chosen to avoid overlap traps (vd=8, vs2=10, vs1=12)

    vtype_lmul_1_e4a27f: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }


    cp_ssstrictv_narrowing_vs2_sew_eq_elen: cross std_trap_vec, vtype_all_sew_supported, vtype_lmul_1_e4a27f;

//// end cp_ssstrictv_narrowing_vs2_sew_eq_elen ////////////////////////////////////////////////////////////////
