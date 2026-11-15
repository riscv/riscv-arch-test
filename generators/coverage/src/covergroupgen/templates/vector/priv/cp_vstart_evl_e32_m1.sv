    //////////////////////////////////////////////////////////////////////////////////
    // cp_vstart
    //////////////////////////////////////////////////////////////////////////////////

    cp_vstart: coverpoint vstart_check_vl(ins.hart, ins.issue, get_vlmax_params(ins.hart, ins.issue, 3'b010, 3'b000)) {
        bins vstart_one     = {vstart_one};
        bins vstart_vlmaxm1 = {vstart_vlmaxm1};
        bins vstart_vlmaxd2 = {vstart_vlmaxd2};
        bins vstart_legal   = {vstart_legal};   // random vstart
    }

    //// end cp_vstart////////////////////////////////////////////////
