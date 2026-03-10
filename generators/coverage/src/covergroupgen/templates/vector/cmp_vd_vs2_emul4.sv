//////////////////////////////////////////////////////////////////////////////////
    // cmp_vd_vs2_emul4
    //////////////////////////////////////////////////////////////////////////////////

    cmp_vd_vs2_emul4 : coverpoint ins.get_vr_reg(ins.current.vd)  iff (ins.current.vd == ins.current.vs2 & ins.trap == 0 )  {
        // Compare assignments of all 32 registers, vd only registers of multiple of 4
        bins v0  = {v0 };
        bins v4  = {v4 };
        bins v8  = {v8 };
        bins v12 = {v12};
        bins v16 = {v16};
        bins v20 = {v20};
        bins v24 = {v24};
        bins v28 = {v28};
    }

    //// end cmp_vd_vs2_emul4////////////////////////////////////////////////
