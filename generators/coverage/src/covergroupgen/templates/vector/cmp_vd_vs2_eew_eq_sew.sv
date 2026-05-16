    //////////////////////////////////////////////////////////////////////////////////
    // cmp_vd_vs2_eew_eq_sew
    //////////////////////////////////////////////////////////////////////////////////

    cmp_vd_vs2_eew_eq_sew : coverpoint ins.get_vr_reg(ins.current.vd)  iff (ins.current.vd == ins.current.vs2 & ins.trap == 0 )  {
        // Compare assignments of all 32 registers (only meaningful when EEW == SEW;
        // testgen filters generation accordingly so non-matching SEWs produce no hits).
    }

    //// end cmp_vd_vs2_eew_eq_sew////////////////////////////////////////////////
