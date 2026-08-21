    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ls_indexed_truncated
    //////////////////////////////////////////////////////////////////////////////////

    `ifdef UDB_MXLEN_32
        vs2_element_zero_top_32_ones_bottom_zero : coverpoint get_vr_element_zero_eew(ins.hart, ins.issue, ins.current.vs2_val, 64) {
            bins target = {64'hFFFF_FFFF_0000_0000};
        }

        cp_custom_ls_indexed_truncated  : cross std_vec, vs2_element_zero_top_32_ones_bottom_zero;
    `endif

    //// end cp_custom_ls_indexed_truncated ////////////////////////////////////////////////
