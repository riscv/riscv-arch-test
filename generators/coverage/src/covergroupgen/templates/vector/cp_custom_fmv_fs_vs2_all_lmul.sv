    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_custom_fmv_fs_vs2_all_lmul
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Scalar read ignores LMUL: vs2 can be any register at any LMUL

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {2};
    }

    vtype_lmul_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {3};
    }

    vs2_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vs2_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vs2_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    cp_custom_voffgroup_vs2_lmul2:    cross std_vec, vtype_lmul_2, vs2_all_reg_unaligned_lmul_2;
    cp_custom_voffgroup_vs2_lmul4:    cross std_vec, vtype_lmul_4, vs2_all_reg_unaligned_lmul_4;
    cp_custom_voffgroup_vs2_lmul8:    cross std_vec, vtype_lmul_8, vs2_all_reg_unaligned_lmul_8;

//// end cp_custom_fmv_fs_vs2_all_lmul ///////////////////////////////////////////////////////////////////////////
