// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ext_emul_lt1_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vzext/vsext overlap with source EMUL < 1 must trap (overlap rule requires src EMUL >= 1)


    // vf2: src_EMUL = LMUL/2 < 1 when LMUL=1, dest=1 reg, overlap = vs2 == vd
    cp_ssstrictv_ext_vf2_emul_lt1: cross std_trap_vec, vtype_lmul_1, vd_eq_vs2;

    // vf4 LMUL=1: src_EMUL=1/4, dest=1 reg, overlap = vs2 == vd
    cp_ssstrictv_ext_vf4_emul_lt1_lmul1: cross std_trap_vec, vtype_lmul_1, vd_eq_vs2;

    // vf4 LMUL=2: src_EMUL=1/2, dest=2 regs, overlap = vs2 in vd's 2-reg group
    cp_ssstrictv_ext_vf4_emul_lt1_lmul2: cross std_trap_vec, vtype_lmul_2, vs2_vd_overlap_lmul1;

    // vf8 LMUL=1: src_EMUL=1/8, dest=1 reg, overlap = vs2 == vd
    cp_ssstrictv_ext_vf8_emul_lt1_lmul1: cross std_trap_vec, vtype_lmul_1, vd_eq_vs2;

    // vf8 LMUL=2: src_EMUL=1/4, dest=2 regs, overlap = vs2 in vd's 2-reg group
    cp_ssstrictv_ext_vf8_emul_lt1_lmul2: cross std_trap_vec, vtype_lmul_2, vs2_vd_overlap_lmul1;

    // vf8 LMUL=4: src_EMUL=1/2, dest=4 regs, overlap = vs2 in vd's 4-reg group
    cp_ssstrictv_ext_vf8_emul_lt1_lmul4: cross std_trap_vec, vtype_lmul_4, vs2_vd_overlap_lmul2;

//// end cp_ssstrictv_ext_emul_lt1_overlap ///////////////////////////////////////////////////////////
