    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vwholeRegLS_lmul
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector whole register load and store operations

    vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                        == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }

    vtype_all_lmulge1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_custom_vwholeRegLS_lmul:     cross std_vec, vl_max, vtype_all_lmulge1;

    //// end cp_custom_vwholeRegLS_lmul////////////////////////////////////////////////
