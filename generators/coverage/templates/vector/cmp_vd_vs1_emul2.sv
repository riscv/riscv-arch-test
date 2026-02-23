//////////////////////////////////////////////////////////////////////////////////
    // cmp_vd_vs1_emul2
    //////////////////////////////////////////////////////////////////////////////////

    cmp_vd_vs1_emul2 : coverpoint ins.get_vr_reg(ins.current.vd)  iff (ins.current.vd == ins.current.vs1 & ins.trap == 0 )  {
        // Compare assignments of all 32 registers, vd only even registers (widen)
        bins v0  = {v0 };
        bins v2  = {v2 };
        bins v4  = {v4 };
        bins v6  = {v6 };
        bins v8  = {v8 };
        bins v10 = {v10};
        bins v12 = {v12};
        bins v14 = {v14};
        bins v16 = {v16};
        bins v18 = {v18};
        bins v20 = {v20};
        bins v22 = {v22};
        bins v24 = {v24};
        bins v26 = {v26};
        bins v28 = {v28};
        bins v30 = {v30};
    }

    //// end cmp_vd_vs1_emul2////////////////////////////////////////////////
