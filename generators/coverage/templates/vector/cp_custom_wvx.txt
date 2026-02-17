//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vdOverlapTopVs2_vd_vs2_lmul4
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector widening operations with vx operands

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

    vd_reg_aligned_lmul_2: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vd_reg_aligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vd_reg_aligned_lmul_8: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vs2_reg_unaligned_lmul_2: coverpoint ins.current.insn[24:20] {
        wildcard bins odd = {5'b????1};
    }

    vs2_mod4_2: coverpoint ins.current.insn[21:20] {
        bins mode4_2 = {2'b10};
    }

    vs2_mod8_4: coverpoint ins.current.insn[22:20] {
        bins mod8_4 = {3'b100};
    }

    cp_custom_vdOverlapTopVs2_vd_vs2_lmul1 : cross std_vec, vtype_lmul_1, vs2_vd_overlap_lmul1, vd_reg_aligned_lmul_2, vs2_reg_unaligned_lmul_2;
    cp_custom_vdOverlapTopVs2_vd_vs2_lmul2 : cross std_vec, vtype_lmul_2, vs2_vd_overlap_lmul2, vd_reg_aligned_lmul_4, vs2_mod4_2;
    cp_custom_vdOverlapTopVs2_vd_vs2_lmul4 : cross std_vec, vtype_lmul_4, vs2_vd_overlap_lmul4, vd_reg_aligned_lmul_8, vs2_mod8_4;

    //// end cp_custom_vdOverlapTopVs2_vd_vs2_lmul4////////////////////////////////////////////////
