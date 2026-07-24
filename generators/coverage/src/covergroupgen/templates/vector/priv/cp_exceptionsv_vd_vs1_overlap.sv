// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_exceptionsv_vd_vs1_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // ExceptionsV: vd overlaps vs1 source register group
    // We cannot test anything dependent on csr state in Ssstrict, potentially there will be another test suite
    // where all reserved encodings are tested, so the dependence on lmul is left as a comment.
    // cp_exceptionsv_vd_vs1_overlap : cross std_trap_vec, vtype_all_lmulge1, vd_eq_vs1;
    cp_exceptionsv_vd_vs1_overlap : cross std_trap_vec, vd_eq_vs1;

//// end cp_exceptionsv_vd_vs1_overlap //////////////////////////////////////////////////////////////////////////////////////////////
