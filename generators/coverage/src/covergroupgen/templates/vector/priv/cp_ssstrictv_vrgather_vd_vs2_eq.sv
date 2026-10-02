// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vrgather_vd_vs2_eq
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // vrgather with vd==vs2 reserved (vd source overlap)
    // We cannot test anything dependent on csr state in Ssstrict, potentially there will be another test suite
    // where all reserved encodings are tested, so the dependence on lmul is left as a comment.
    // cp_ssstrictv_vrgather_vd_vs2_eq : cross std_trap_vec, vtype_all_lmulge1, vd_eq_vs2;
    cp_ssstrictv_vrgather_vd_vs2_eq : cross std_trap_vec, vd_eq_vs2;

//// end cp_ssstrictv_vrgather_vd_vs2_eq //////////////////////////////////////////////////////////////////////////////////////////////
