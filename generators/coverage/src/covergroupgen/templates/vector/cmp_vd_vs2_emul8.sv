//////////////////////////////////////////////////////////////////////////////////
    // cmp_vd_vs2_emul8
    //////////////////////////////////////////////////////////////////////////////////

    cmp_vd_vs2_emul8 : coverpoint ins.get_vr_reg(ins.current.vd)  iff (ins.current.vd == ins.current.vs2 & ins.trap == 0 )  {
        // Compare assignments of all 32 registers, vd only registers of multiple of 8
        bins v0  = {v0 };
        bins v8  = {v8 };
        bins v16 = {v16};
        bins v24 = {v24};
    }

    //// end cmp_vd_vs2_emul8////////////////////////////////////////////////
