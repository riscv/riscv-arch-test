    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_NaN_input
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    vs2_element0_sqNAN : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        `ifdef COVER_VFCUSTOM16
            bins vs2_0_qNaN = {64'h0000_0000_0000_7E00}; // qNaN input (canonical half)
            bins vs2_0_sNaN = {64'h0000_0000_0000_7D00}; // sNaN input (half)
        `endif
        `ifdef COVER_VFCUSTOM32
            bins vs2_0_qNaN = {64'h0000_0000_7FC0_0000}; // qNaN input (canonical single)
            bins vs2_0_sNaN = {64'h0000_0000_7FA0_0000}; // sNaN input (single)
        `endif
    }

    cp_custom_vfp_NaN_input : cross std_vec, vs2_element0_sqNAN;
`else
    `ifdef FLEN64
    vs2_element0_sqNAN : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
            bins vs2_0_qNaN = {64'h7FF8_0000_0000_0000}; // qNaN input (canonical double)
            bins vs2_0_sNaN = {64'h7FF0_0000_0000_0001}; // sNaN input (double)
    }

    cp_custom_vfp_NaN_input : cross std_vec, vs2_element0_sqNAN;
    `endif
`endif

    //// end cp_custom_vfp_NaN_input////////////////////////////////////////////////
