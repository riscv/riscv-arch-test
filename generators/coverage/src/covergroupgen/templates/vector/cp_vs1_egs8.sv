    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs1_egs8
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs1_egs8 : coverpoint ins.get_vr_reg(ins.current.vs1)  iff (ins.trap == 0 )  {
        // VS1 register assignment (EGS=8, SEW=32: with VLEN=128 LMUL=2 is required, so odd registers are illegal, with VLEN=32, LMUL=4
        // is required so all registers must be a multiple of 4, and with VLEN=32 LMUL=8 is required, so all registers must be a multiple of 8)
        `ifndef ZVL256B_SUPPORTED
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

        `ifndef ZVL128B_SUPPORTED
            ignore_bins v2  = {v2};
            ignore_bins v6  = {v6};
            ignore_bins v10  = {v10};
            ignore_bins v14  = {v14};
            ignore_bins v18  = {v18};
            ignore_bins v22 = {v22};
            ignore_bins v26 = {v26};
            ignore_bins v30 = {v30};
        `endif

        `ifndef ZVL64B_SUPPORTED
            ignore_bins v4  = {v4};
            ignore_bins v12  = {v12};
            ignore_bins v20  = {v20};
            ignore_bins v28  = {v28};
        `endif
    }

    //// end cp_vs1_egs8 ////////////////////////////////////////////////
