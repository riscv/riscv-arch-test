    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ls_indexed
    //////////////////////////////////////////////////////////////////////////////////

    `ifdef UDB_MXLEN_32
    `ifdef COVER_VLS64
        vs2_element_zero_top_32_ones_bottom_zero : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
            bins target = {64'hFFFF_FFFF_0000_0000};
        }

        vtype_sew_64: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
            bins e64 = {3};
        }

        cp_custom_ls_indexed_truncated  : cross std_vec, vtype_sew_64, vs2_element_zero_top_32_ones_bottom_zero;
    `endif
    `endif

    //// end cp_custom_ls_indexed////////////////////////////////////////////////
