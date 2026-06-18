    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1/2/4
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector shift and clip instructions with wi operands

    // ensures vd updates
    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;
    all_std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }


    all_vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }

    all_vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    all_vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {2};
    }

    all_vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }

    all_vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
        bins overlapping = {1'b1};
    }

    all_vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
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

    all_vd_eq_vs2 : coverpoint ins.current.insn[24:20] == ins.current.insn[11:7] {
        bins true = {1'b1};
    }

    cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1: cross all_std_vec, all_vtype_lmul_1, all_vs2_vd_overlap_lmul1, all_vd_eq_vs2, vs2_all_reg_aligned_lmul_2;
    cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul2: cross all_std_vec, all_vtype_lmul_2, all_vs2_vd_overlap_lmul2, all_vd_eq_vs2, vs2_all_reg_aligned_lmul_4;
    cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4: cross all_std_vec, all_vtype_lmul_4, all_vs2_vd_overlap_lmul4, all_vd_eq_vs2, vs2_all_reg_aligned_lmul_8;

    //// end cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1/2/4 ////////////////////////////////////////////////
