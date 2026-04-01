    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_edges
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    `ifdef COVER_VFCUSTOM16
    FpRecEst_sig_in : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[9:3] {
        // all bins
    }
    cp_custom_FpRecipEst_edges: cross std_vec, FpRecEst_sig_in;
    `elsif COVER_VFCUSTOM32
    FpRecEst_sig_in : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[22:16] {
        // all bins
    }
    cp_custom_FpRecipEst_edges: cross std_vec, FpRecEst_sig_in;
    `endif
`else
    `ifdef FLEN64
    FpRecEst_sig_in : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[51:45] {
        // all bins
    }

    cp_custom_FpRecipEst_edges: cross std_vec, FpRecEst_sig_in;
    `endif
`endif

    //// end cp_custom_FpRecipEst_edges////////////////////////////////////////////////
