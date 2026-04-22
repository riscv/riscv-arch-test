    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ls_indexed
    //////////////////////////////////////////////////////////////////////////////////

    `ifdef COVER_VLS8
    vs2_element_zero_minus1_sew8 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        wildcard bins target = {64'b????????_????????_????????_11111111};
    }

    vtype_sew_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e8 = {0};
    }

    cp_custom_ls_indexed_zero_extended_sew8   : cross std_vec, vs2_element_zero_minus1_sew8,  vtype_sew_8;
    `endif

    `ifdef COVER_VLS16
    vs2_element_zero_minus1_sew16 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        wildcard bins target = {64'b????????_????????_11111111_11111111};
    }

    vtype_sew_16: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e16 = {1};
    }

    cp_custom_ls_indexed_zero_extended_sew16  : cross std_vec, vs2_element_zero_minus1_sew16, vtype_sew_16;
    `endif

    `ifdef XLEN32
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
