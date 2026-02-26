    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_NaN_input
    //////////////////////////////////////////////////////////////////////////////////

    vfp_NaN_input_fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") {
        bins clear = {0};
    }

    vs2_element0_sqNAN : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        `ifdef COVER_VFCUSTOM16
            bins vs2_0_qNaN = {64'h0000_0000_0000_7E00}; // qNaN input (canonical half)
            bins vs2_0_sNaN = {64'h0000_0000_0000_7D00}; // sNaN input (half)
        `endif
        `ifdef COVER_VFCUSTOM32
            bins vs2_0_qNaN = {64'h0000_0000_7FC0_0000}; // qNaN input (canonical single)
            bins vs2_0_sNaN = {64'h0000_0000_7FA0_0000}; // sNaN input (single)
        `endif
        `ifdef COVER_VFCUSTOM64
            bins vs2_0_qNaN = {64'h7FF8_0000_0000_0000}; // qNaN input (canonical double)
            bins vs2_0_sNaN = {64'h7FF0_0000_0000_0001}; // sNaN input (double)
        `endif
    }

    cp_custom_vfp_NaN_input : cross std_vec, vfp_NaN_input_fp_flags_clear, vs2_element0_sqNAN;

    //// end cp_custom_vfp_NaN_input////////////////////////////////////////////////
