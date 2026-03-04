//////////////////////////////////////////////////////////////////////////////////
    // cp_vs3_lte24
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs3_lte24 : coverpoint ins.get_vr_reg(ins.current.vs3)  iff (ins.trap == 0 )  {
        // VD register assignment excluding bins
        ignore_bins v31 = {v31};
        ignore_bins v30 = {v30};
        ignore_bins v29 = {v29};
        ignore_bins v28 = {v28};
        ignore_bins v27 = {v27};
        ignore_bins v26 = {v26};
        ignore_bins v25 = {v25};
    }

    //// end cp_vs3_lte24////////////////////////////////////////////////
