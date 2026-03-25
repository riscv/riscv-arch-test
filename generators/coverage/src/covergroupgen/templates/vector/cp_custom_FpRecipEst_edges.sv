    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_edges
    //////////////////////////////////////////////////////////////////////////////////

    FpRecEst_sig_in : coverpoint
    `ifdef COVER_VFCUSTOM16
    get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[9:3]
    `endif
    `ifdef COVER_VFCUSTOM32
    get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[22:16]
    `endif
    `ifdef COVER_VFCUSTOM64
    get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[51:45]
    `endif
    {
        // all bins
    }

    cp_custom_FpRecipEst_edges: cross std_vec, FpRecEst_sig_in;

    //// end cp_custom_FpRecipEst_edges////////////////////////////////////////////////
