//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vindexEdges_index_gt_vl_lt_vlmax
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector slidedown and gather instructions

    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;


    vtype_sew_elemt_zero_vs1_all_ones_sew32 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],  get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)} {
        wildcard bins sew32     = {66'b10_????????_????????_????????_????????_11111111_11111111_11111111_11111111};
    }

    cp_custom_vindexEdges_index_ge_vlmax : cross std_vec, vtype_sew_elemt_zero_vs1_all_ones_sew32;

    //////////////////////////////////////////////////////////////////////////////////

    vl_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins one = {1};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vtype_sew_elemt_zero_vs1_2_sew32 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],  get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)} {
        wildcard bins sew32     = {66'b10_????????_????????_????????_????????_00000000_00000000_00000000_00000010};
    }

    cp_custom_vindexEdges_index_gt_vl_lt_vlmax :   cross std_vec, vl_one, vtype_lmul_2, vtype_sew_elemt_zero_vs1_2_sew32;

    //// end cp_custom_vindexEdges_index_gt_vl_lt_vlmax////////////////////////////////////////////////
