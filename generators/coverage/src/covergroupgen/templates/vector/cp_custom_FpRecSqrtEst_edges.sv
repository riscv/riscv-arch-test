    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FPrecSqrt_edges
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    `ifdef COVER_VFCUSTOM16
    FpRecSqrtEst_all_inputs_vs2_0 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[10:4] {
        // all bins
    }
    cp_custom_FpRecSqrtEst_edges: cross std_vec, FpRecSqrtEst_all_inputs_vs2_0;
    `elsif COVER_VFCUSTOM32
    FpRecSqrtEst_all_inputs_vs2_0 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[23:17] {
        // all bins
    }
    cp_custom_FpRecSqrtEst_edges: cross std_vec, FpRecSqrtEst_all_inputs_vs2_0;
    `endif
`else
    `ifdef FLEN64
    FpRecSqrtEst_all_inputs_vs2_0 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[52:46] {
        // all bins
    }

    cp_custom_FpRecSqrtEst_edges: cross std_vec, FpRecSqrtEst_all_inputs_vs2_0;
    `endif
`endif

    //// end cp_custom_FPrecSqrt_edges////////////////////////////////////////////////
