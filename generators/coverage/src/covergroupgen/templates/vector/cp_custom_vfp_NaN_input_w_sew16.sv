    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_NaN_input
    //////////////////////////////////////////////////////////////////////////////////

    vs2_element0_sqNAN : coverpoint get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs2_val) {
        bins vs2_0_qNaN = {64'h0000_0000_7FC0_0000}; // qNaN input (canonical single)
        bins vs2_0_sNaN = {64'h0000_0000_7FA0_0000}; // sNaN input (single)
    }

    cp_custom_vfp_NaN_input : cross std_vec, vs2_element0_sqNAN;

    //// end cp_custom_vfp_NaN_input////////////////////////////////////////////////
