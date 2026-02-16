    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FPrecSqrt_flag_edges
    //////////////////////////////////////////////////////////////////////////////////
    fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") {
            bins clear = {0};
    }

    vs1_0_reciprocal_sqrt_edges : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1) {
        // -∞ ≤ x < -0.0   (representative negative finite: -1.0)
        `ifdef COVER_VFCUSTOM16
            // -1.0h = 0xBC00
            bins vs1_0_neg_finite = {64'h0000_0000_0000_BC00};
            // -Inf_h = 0xFC00
            bins vs1_0_neg_inf    = {64'h0000_0000_0000_FC00};
            // -0.0h = 0x8000
            bins vs1_0_neg_zero   = {64'h0000_0000_0000_8000};

            // +0.0h = 0x0000
            bins vs1_0_pos_zero   = {64'h0000_0000_0000_0000};
            // +Inf_h = 0x7C00
            bins vs1_0_pos_inf    = {64'h0000_0000_0000_7C00};
            // +1.0h = 0x3C00
            bins vs1_0_pos_finite = {64'h0000_0000_0000_3C00};

            // qNaN_h canonical = 0x7E00
            bins vs1_0_qNaN       = {64'h0000_0000_0000_7E00};
            // sNaN_h example = 0x7D00
            bins vs1_0_sNaN       = {64'h0000_0000_0000_7D00};
        `endif

        `ifdef COVER_VFCUSTOM32
            // -1.0f = 0xBF800000
            bins vs1_0_neg_finite = {64'h0000_0000_BF80_0000};
            // -Inf_f = 0xFF800000
            bins vs1_0_neg_inf    = {64'h0000_0000_FF80_0000};
            // -0.0f = 0x80000000
            bins vs1_0_neg_zero   = {64'h0000_0000_8000_0000};

            // +0.0f = 0x00000000
            bins vs1_0_pos_zero   = {64'h0000_0000_0000_0000};
            // +Inf_f = 0x7F800000
            bins vs1_0_pos_inf    = {64'h0000_0000_7F80_0000};
            // +1.0f = 0x3F800000
            bins vs1_0_pos_finite = {64'h0000_0000_3F80_0000};

            // qNaN_f canonical = 0x7FC00000
            bins vs1_0_qNaN       = {64'h0000_0000_7FC0_0000};
            // sNaN_f example = 0x7FA00000
            bins vs1_0_sNaN       = {64'h0000_0000_7FA0_0000};
        `endif

        `ifdef COVER_VFCUSTOM64
            // -1.0d = 0xBFF0000000000000
            bins vs1_0_neg_finite = {64'hBFF0_0000_0000_0000};
            // -Inf_d = 0xFFF0000000000000
            bins vs1_0_neg_inf    = {64'hFFF0_0000_0000_0000};
            // -0.0d = 0x8000000000000000
            bins vs1_0_neg_zero   = {64'h8000_0000_0000_0000};

            // +0.0d = 0x0000000000000000
            bins vs1_0_pos_zero   = {64'h0000_0000_0000_0000};
            // +Inf_d = 0x7FF0000000000000
            bins vs1_0_pos_inf    = {64'h7FF0_0000_0000_0000};
            // +1.0d = 0x3FF0000000000000
            bins vs1_0_pos_finite = {64'h3FF0_0000_0000_0000};

            // qNaN_d canonical = 0x7FF8000000000000
            bins vs1_0_qNaN       = {64'h7FF8_0000_0000_0000};
            // sNaN_d example = 0x7FF0000000000001
            bins vs1_0_sNaN       = {64'h7FF0_0000_0000_0001};
        `endif
    }

    cp_custom_FpRecSqrtEst_flag_edges: cross std_vec, vs1_0_reciprocal_sqrt_edges, fp_flags_clear;

    //// end cp_custom_FPrecSqrt_flag_edges////////////////////////////////////////////////
