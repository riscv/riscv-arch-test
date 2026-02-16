//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vshiftn_upperbits_rs1_ones
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector shift and clip instructions with wx operands

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

    vd_eq_vs2 : coverpoint ins.current.insn[24:20] == ins.current.insn[11:7] {
        bins true = {1'b1};
    }

    vs2_reg_aligned_lmul_2: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vs2_reg_aligned_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vs2_reg_aligned_lmul_8: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_8 = {5'b??000};
    }

    cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1: cross std_vec, vtype_lmul_1, vs2_vd_overlap_lmul1, vd_eq_vs2, vs2_reg_aligned_lmul_2;
    cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2: cross std_vec, vtype_lmul_2, vs2_vd_overlap_lmul2, vd_eq_vs2, vs2_reg_aligned_lmul_4;
    cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4: cross std_vec, vtype_lmul_4, vs2_vd_overlap_lmul4, vd_eq_vs2, vs2_reg_aligned_lmul_8;

    rs1_top_bits_one_cross_sew8 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],  ins.current.rs1_val} {
        `ifdef XLEN32
        wildcard bins sew8      = {34'b00_????????_????????_11111111_1111????};
        `endif

        `ifdef XLEN64
        wildcard bins sew8      = {66'b00_????????_????????_????????_????????_????????_????????_11111111_1111????};
        `endif
    }

    cp_custom_vshiftn_upperbits_rs1_ones : cross std_vec, rs1_top_bits_one_cross_sew8;

    //// end cp_custom_vshiftn_upperbits_rs1_ones////////////////////////////////////////////////
