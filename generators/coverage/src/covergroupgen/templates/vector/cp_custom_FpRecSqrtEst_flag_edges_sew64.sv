    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FPrecSqrt_flag_edges
    //////////////////////////////////////////////////////////////////////////////////

    fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0] {
        bins clear = {0};
    }

    vs2_0_reciprocal_sqrt_edges : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        // -1.0d = 0xBFF0000000000000
        bins vs2_0_neg_finite = {64'hBFF0_0000_0000_0000};
        // -Inf_d = 0xFFF0000000000000
        bins vs2_0_neg_inf    = {64'hFFF0_0000_0000_0000};
        // -0.0d = 0x8000000000000000
        bins vs2_0_neg_zero   = {64'h8000_0000_0000_0000};

        // +0.0d = 0x0000000000000000
        bins vs2_0_pos_zero   = {64'h0000_0000_0000_0000};
        // +Inf_d = 0x7FF0000000000000
        bins vs2_0_pos_inf    = {64'h7FF0_0000_0000_0000};
        // +1.0d = 0x3FF0000000000000
        bins vs2_0_pos_finite = {64'h3FF0_0000_0000_0000};

        // qNaN_d canonical = 0x7FF8000000000000
        bins vs2_0_qNaN       = {64'h7FF8_0000_0000_0000};
        // sNaN_d example = 0x7FF0000000000001
        bins vs2_0_sNaN       = {64'h7FF0_0000_0000_0001};
    }

    cp_custom_FpRecSqrtEst_flag_edges: cross std_vec, vs2_0_reciprocal_sqrt_edges, fp_flags_clear;

    //// end cp_custom_FPrecSqrt_flag_edges////////////////////////////////////////////////
