    //////////////////////////////////////////////////////////////////////////////////
    // cp_vstart
    //////////////////////////////////////////////////////////////////////////////////

    vstart_vals: coverpoint vstart_check(ins.hart, ins.issue) {
        bins vstart_one     = {vstart_one};
        bins vstart_vlmaxm1 = {vstart_vlmaxm1};
        bins vstart_vlmaxd2 = {vstart_vlmaxd2};
        bins vstart_legal   = {vstart_legal};   // random vstart
    }

    vl_eq_vlmax: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)
    {
        bins true = { 1 };
    }

    cp_vstart: cross vstart_vals, vl_eq_vlmax;

    //// end cp_vstart////////////////////////////////////////////////
