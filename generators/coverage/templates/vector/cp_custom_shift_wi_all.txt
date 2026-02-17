//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector shift and clip instructions with wi operands

    // ensures vd updates
    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;


    vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {2};
    }

    vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }

    vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
        bins overlapping = {1'b1};
    }

    vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
        bins overlapping = {1'b1};
    }

    vs2_all_reg_aligned_lmul_2: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins odd = {5'b????1};
    }

    vs2_all_reg_aligned_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins end_1 = {5'b???01};
        wildcard ignore_bins end_2 = {5'b???10};
        wildcard ignore_bins end_3 = {5'b???11};
    }

    vs2_all_reg_aligned_lmul_8: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins end_1 = {5'b??001};
        wildcard ignore_bins end_2 = {5'b??010};
        wildcard ignore_bins end_3 = {5'b??011};
        wildcard ignore_bins end_4 = {5'b??101};
        wildcard ignore_bins end_5 = {5'b??110};
        wildcard ignore_bins end_6 = {5'b??111};
        wildcard ignore_bins end_7 = {5'b??100};
    }

    vd_eq_vs2 : coverpoint ins.current.insn[24:20] == ins.current.insn[11:7] {
        bins true = {1'b1};
    }

    cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1: cross std_vec, vtype_lmul_1, vs2_vd_overlap_lmul1, vd_eq_vs2, vs2_all_reg_aligned_lmul_2;
    cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul2: cross std_vec, vtype_lmul_2, vs2_vd_overlap_lmul2, vd_eq_vs2, vs2_all_reg_aligned_lmul_4;
    cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4: cross std_vec, vtype_lmul_4, vs2_vd_overlap_lmul4, vd_eq_vs2, vs2_all_reg_aligned_lmul_8;

    //// end cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4////////////////////////////////////////////////
