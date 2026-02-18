//////////////////////////////////////////////////////////////////////////////////
    // cp_vd_lte25
    //////////////////////////////////////////////////////////////////////////////////

    cp_vd_lte25 : coverpoint ins.get_vr_reg(ins.current.vd)  iff (ins.trap == 0 )  {
        // VD register assignment excluding bins
        ignore_bins v31 = {v31};
        ignore_bins v30 = {v30};
        ignore_bins v29 = {v29};
        ignore_bins v28 = {v28};
        ignore_bins v27 = {v27};
        ignore_bins v26 = {v26};
    }

    //// end cp_vd_lte25////////////////////////////////////////////////
