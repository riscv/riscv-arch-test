    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FPrecSqrt_flag_edges
    //////////////////////////////////////////////////////////////////////////////////

    fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0] {
        bins clear = {0};
    }

    vs2_0_reciprocal_sqrt_edges : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        // -1.0f = 0xBF800000
        bins vs2_0_neg_finite = {64'h0000_0000_BF80_0000};
        // -Inf_f = 0xFF800000
        bins vs2_0_neg_inf    = {64'h0000_0000_FF80_0000};
        // -0.0f = 0x80000000
        bins vs2_0_neg_zero   = {64'h0000_0000_8000_0000};

        // +0.0f = 0x00000000
        bins vs2_0_pos_zero   = {64'h0000_0000_0000_0000};
        // +Inf_f = 0x7F800000
        bins vs2_0_pos_inf    = {64'h0000_0000_7F80_0000};
        // +1.0f = 0x3F800000
        bins vs2_0_pos_finite = {64'h0000_0000_3F80_0000};

        // qNaN_f canonical = 0x7FC00000
        bins vs2_0_qNaN       = {64'h0000_0000_7FC0_0000};
        // sNaN_f payload1 = 0x7F800001
        bins vs2_0_sNaN       = {64'h0000_0000_7F80_0001};
    }

    cp_custom_FpRecSqrtEst_flag_edges: cross std_vec, vs2_0_reciprocal_sqrt_edges, fp_flags_clear;

    //// end cp_custom_FPrecSqrt_flag_edges////////////////////////////////////////////////
