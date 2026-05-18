    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs1_egs4
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs1_egs4 : coverpoint ins.get_vr_reg(ins.current.vs1)  iff (ins.trap == 0 )  {
        // VS1 register assignment (EGS=4, SEW=32: with VLEN=64 LMUL=2 is required, so odd registers are illegal)
        `ifndef ZVL128B_SUPPORTED
            ignore_bins v1  = {v1};
            ignore_bins v3  = {v3};
            ignore_bins v5  = {v5};
            ignore_bins v7  = {v7};
            ignore_bins v9  = {v9};
            ignore_bins v11 = {v11};
            ignore_bins v13 = {v13};
            ignore_bins v15 = {v15};
            ignore_bins v17 = {v17};
            ignore_bins v19 = {v19};
            ignore_bins v21 = {v21};
            ignore_bins v23 = {v23};
            ignore_bins v25 = {v25};
            ignore_bins v27 = {v27};
            ignore_bins v29 = {v29};
            ignore_bins v31 = {v31};
        `endif
    }

    //// end cp_vs1_egs4////////////////////////////////////////////////
