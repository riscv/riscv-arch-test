//////////////////////////////////////////////////////////////////////////////////
    // cp_vs3_emul8
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs3_emul8 : coverpoint ins.get_vr_reg(ins.current.vs3) iff (ins.trap == 0) {
        // VD register assignment (widening instruction, including only registers of multiple of 8)
        ignore_bins v1 = {v1};
        ignore_bins v2 = {v2};
        ignore_bins v3 = {v3};
        ignore_bins v4 = {v4};
        ignore_bins v5 = {v5};
        ignore_bins v6 = {v6};
        ignore_bins v7 = {v7};
        ignore_bins v9 = {v9};
        ignore_bins v10 = {v10};
        ignore_bins v11 = {v11};
        ignore_bins v12 = {v12};
        ignore_bins v13 = {v13};
        ignore_bins v14 = {v14};
        ignore_bins v15 = {v15};
        ignore_bins v17 = {v17};
        ignore_bins v18 = {v18};
        ignore_bins v19 = {v19};
        ignore_bins v20 = {v20};
        ignore_bins v21 = {v21};
        ignore_bins v22 = {v22};
        ignore_bins v23 = {v23};
        ignore_bins v25 = {v25};
        ignore_bins v26 = {v26};
        ignore_bins v27 = {v27};
        ignore_bins v28 = {v28};
        ignore_bins v29 = {v29};
        ignore_bins v30 = {v30};
        ignore_bins v31 = {v31};
    }

    //// end cp_vs3_emul8////////////////////////////////////////////////
