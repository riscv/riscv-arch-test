    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_maskLS
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector mask load/store operations

    // --- EMUL >= 16 (LMUL > 1 and SEW > 8) ---

    vtype_all_lmulgt1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_custom_maskLS_emul_ge_16             : cross std_vec, vtype_all_lmulgt1;

    //// end cp_custom_maskLS////////////////////////////////////////////////
