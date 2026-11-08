    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FPrecSqrt_flag_edges
    //////////////////////////////////////////////////////////////////////////////////

    fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0] {
        bins clear = {0};
    }

    vs2_0_reciprocal_sqrt_edges : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        // -1.0h = 0xBC00
        bins vs2_0_neg_finite = {64'h0000_0000_0000_BC00};
        // -Inf_h = 0xFC00
        bins vs2_0_neg_inf    = {64'h0000_0000_0000_FC00};
        // -0.0h = 0x8000
        bins vs2_0_neg_zero   = {64'h0000_0000_0000_8000};

        // +0.0h = 0x0000
        bins vs2_0_pos_zero   = {64'h0000_0000_0000_0000};
        // +Inf_h = 0x7C00
        bins vs2_0_pos_inf    = {64'h0000_0000_0000_7C00};
        // +1.0h = 0x3C00
        bins vs2_0_pos_finite = {64'h0000_0000_0000_3C00};

        // qNaN_h canonical = 0x7E00
        bins vs2_0_qNaN       = {64'h0000_0000_0000_7E00};
        // sNaN_h payload1 = 0x7D01
        bins vs2_0_sNaN       = {64'h0000_0000_0000_7D01};
    }

    cp_custom_FpRecSqrtEst_flag_edges: cross std_vec, vs2_0_reciprocal_sqrt_edges, fp_flags_clear;

    //// end cp_custom_FPrecSqrt_flag_edges////////////////////////////////////////////////
