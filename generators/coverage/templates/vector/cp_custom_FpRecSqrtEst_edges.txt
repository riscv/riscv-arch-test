    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FPrecSqrt_edges
    //////////////////////////////////////////////////////////////////////////////////

    FpRecSqrtEst_all_inputs_vs2_0 : coverpoint
    `ifdef COVER_VFCUSTOM16
    get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[10:4]
    `endif
    `ifdef COVER_VFCUSTOM32
    get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[23:17]
    `endif
    `ifdef COVER_VFCUSTOM64
    get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[52:46]
    `endif
    {
        // all bins
    }


    cp_custom_FpRecSqrtEst_edges: cross std_vec, FpRecSqrtEst_all_inputs_vs2_0;

    //// end cp_custom_FPrecSqrt_edges////////////////////////////////////////////////
