    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_NaN_input
    //////////////////////////////////////////////////////////////////////////////////

    vs2_element0_sqNAN : coverpoint get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs2_val) {
        bins vs2_0_qNaN = {64'h0000_0000_0000_7E00}; // qNaN input (canonical half)
        bins vs2_0_sNaN = {64'h0000_0000_0000_7D00}; // sNaN input (half)
    }

    cp_custom_vfp_NaN_input : cross std_vec, vs2_element0_sqNAN;

    //// end cp_custom_vfp_NaN_input////////////////////////////////////////////////
