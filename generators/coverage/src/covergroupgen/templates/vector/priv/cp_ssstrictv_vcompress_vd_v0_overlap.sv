// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcompress_vd_v0_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vcompress: destination register group cannot overlap source mask register (v0)
    cp_ssstrictv_vcompress_vd_v0_overlap: cross std_trap_vec, vd_v0;

    // We cannot test anything dependent on csr state in Ssstrict, potentially there will be another test suite
    // where all reserved encodings are tested, so the dependence on lmul is left as a comment.
    // cp_ssstrictv_vcompress_vd_v0_overlap_lmul1: cross std_trap_vec, vtype_lmul_1, vd_v0;

    // cp_ssstrictv_vcompress_vd_v0_overlap_lmul2: cross std_trap_vec, vtype_lmul_2, vd_v0;

    // cp_ssstrictv_vcompress_vd_v0_overlap_lmul4: cross std_trap_vec, vtype_lmul_4, vd_v0;

    // cp_ssstrictv_vcompress_vd_v0_overlap_lmul8: cross std_trap_vec, vtype_lmul_8, vd_v0;

//// end cp_ssstrictv_vcompress_vd_v0_overlap ///////////////////////////////////////////////////////////////
