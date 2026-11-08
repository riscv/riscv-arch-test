    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_NaN_input
    //////////////////////////////////////////////////////////////////////////////////

    vs2_element0_sqNAN : coverpoint get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs2_val) {
        bins vs2_0_qNaN = {64'h7FF8_0000_0000_0000}; // qNaN input (canonical double)
        bins vs2_0_sNaN = {64'h7FF0_0000_0000_0001}; // sNaN input (double)
    }

    cp_custom_vfp_NaN_input : cross std_vec, vs2_element0_sqNAN;

    //// end cp_custom_vfp_NaN_input////////////////////////////////////////////////
