//////////////////////////////////////////////////////////////////////////////////
    // cmp_vs3_vs2_lte26
    //////////////////////////////////////////////////////////////////////////////////

    cmp_vs3_vs2_lte26 : coverpoint ins.get_vr_reg(ins.current.vs3)  iff (ins.current.vs3 == ins.current.vs2 & ins.trap == 0 )  {
        ignore_bins v31 = {v31};
        ignore_bins v30 = {v30};
        ignore_bins v29 = {v29};
        ignore_bins v28 = {v28};
        ignore_bins v27 = {v27};
    }

    //// end cmp_vs3_vs2_lte26////////////////////////////////////////////////
