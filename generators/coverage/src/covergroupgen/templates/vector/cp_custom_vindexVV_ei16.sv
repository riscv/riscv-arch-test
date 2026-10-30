    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vindexEdges_index_gt_vl_lt_vlmax
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector slidedown and gather instructions

    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;
    elemt_zero_vs1_all_ones_eew16 : coverpoint get_vr_element_zero_eew(ins.hart, ins.issue, ins.current.vs1_val, 16) {
        bins eew16     = {16'b11111111_11111111};
    }

    cp_custom_vindexEdges_index_ge_vlmax : cross std_vec, elemt_zero_vs1_all_ones_eew16;

    //////////////////////////////////////////////////////////////////////////////////

    vl_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins one = {1};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    elemt_zero_vs1_2_eew16 : coverpoint get_vr_element_zero_eew(ins.hart, ins.issue, ins.current.vs1_val, 16) {
        bins eew16     = {16'b00000000_00000010};
    }

    cp_custom_vindexEdges_index_gt_vl_lt_vlmax :   cross std_vec, vl_one, vtype_lmul_2, elemt_zero_vs1_2_eew16;

    //// end cp_custom_vindexEdges_index_gt_vl_lt_vlmax////////////////////////////////////////////////
