    //////////////////////////////////////////////////////////////////////////////////
    // cmp_vs3_vs2_eew_eq_sew
    //////////////////////////////////////////////////////////////////////////////////

    cmp_vs3_vs2_eew_eq_sew : coverpoint ins.get_vr_reg(ins.current.vs3)  iff (ins.current.vs3 == ins.current.vs2 & ins.trap == 0 )  {
        // Compare assignments of all 32 registers (only meaningful when EEW == SEW;
        // testgen filters generation accordingly so non-matching SEWs produce no hits).
    }

    //// end cmp_vs3_vs2_eew_eq_sew////////////////////////////////////////////////
