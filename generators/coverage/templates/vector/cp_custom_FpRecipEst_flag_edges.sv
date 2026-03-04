    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_flag_edges
    //////////////////////////////////////////////////////////////////////////////////
    fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") {
            bins clear = {0};
    }

    vs1_0_recip7_edges : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1) {
        `ifdef COVER_VFCUSTOM16
            bins vs1_0_neg_inf        = {64'h0000_0000_0000_FC00}; // -∞
            bins vs1_0_neg_zero       = {64'h0000_0000_0000_8000}; // -0.0

            bins vs1_0_neg_sub_tiny   = {64'h0000_0000_0000_8001}; // negative subnormal, tiny magnitude
            bins vs1_0_neg_sub_big    = {64'h0000_0000_0000_83FF}; // negative subnormal, larger magnitude

            bins vs1_0_neg_norm_small = {64'h0000_0000_0000_BC00}; // negative normal, small magnitude (e.g., -1.0)
            bins vs1_0_neg_norm_big   = {64'h0000_0000_0000_FBFF}; // negative normal, large magnitude (near -max finite)

            bins vs1_0_pos_zero       = {64'h0000_0000_0000_0000}; // +0.0

            bins vs1_0_pos_sub_tiny   = {64'h0000_0000_0000_0001}; // positive subnormal, tiny magnitude
            bins vs1_0_pos_sub_big    = {64'h0000_0000_0000_03FF}; // positive subnormal, larger magnitude

            bins vs1_0_pos_norm_small = {64'h0000_0000_0000_3C00}; // positive normal, small magnitude (e.g., +1.0)
            bins vs1_0_pos_norm_big   = {64'h0000_0000_0000_7BFF}; // positive normal, large magnitude (near max finite)

            bins vs1_0_pos_inf        = {64'h0000_0000_0000_7C00}; // +∞

            bins vs1_0_qNaN           = {64'h0000_0000_0000_7E00}; // qNaN input (canonical)
            bins vs1_0_sNaN           = {64'h0000_0000_0000_7D00}; // sNaN input (example)
        `endif
        `ifdef COVER_VFCUSTOM32
            bins vs1_0_neg_inf        = {64'h0000_0000_FF80_0000}; // -∞
            bins vs1_0_neg_zero       = {64'h0000_0000_8000_0000}; // -0.0

            bins vs1_0_neg_sub_tiny   = {64'h0000_0000_8000_0001}; // negative subnormal, tiny magnitude
            bins vs1_0_neg_sub_big    = {64'h0000_0000_807F_FFFF}; // negative subnormal, larger magnitude

            bins vs1_0_neg_norm_small = {64'h0000_0000_BF80_0000}; // negative normal, small magnitude (e.g., -1.0)
            bins vs1_0_neg_norm_big   = {64'h0000_0000_FF7F_FFFF}; // negative normal, large magnitude (near -max finite)

            bins vs1_0_pos_zero       = {64'h0000_0000_0000_0000}; // +0.0

            bins vs1_0_pos_sub_tiny   = {64'h0000_0000_0000_0001}; // positive subnormal, tiny magnitude
            bins vs1_0_pos_sub_big    = {64'h0000_0000_007F_FFFF}; // positive subnormal, larger magnitude

            bins vs1_0_pos_norm_small = {64'h0000_0000_3F80_0000}; // positive normal, small magnitude (e.g., +1.0)
            bins vs1_0_pos_norm_big   = {64'h0000_0000_7F7F_FFFF}; // positive normal, large magnitude (near max finite)

            bins vs1_0_pos_inf        = {64'h0000_0000_7F80_0000}; // +∞

            bins vs1_0_qNaN           = {64'h0000_0000_7FC0_0000}; // qNaN input (canonical)
            bins vs1_0_sNaN           = {64'h0000_0000_7FA0_0000}; // sNaN input (example)
        `endif
        `ifdef COVER_VFCUSTOM64
            bins vs1_0_neg_inf        = {64'hFFF0_0000_0000_0000}; // -∞
            bins vs1_0_neg_zero       = {64'h8000_0000_0000_0000}; // -0.0

            bins vs1_0_neg_sub_tiny   = {64'h8000_0000_0000_0001}; // negative subnormal, tiny magnitude
            bins vs1_0_neg_sub_big    = {64'h800F_FFFF_FFFF_FFFF}; // negative subnormal, larger magnitude

            bins vs1_0_neg_norm_small = {64'hBFF0_0000_0000_0000}; // negative normal, small magnitude (e.g., -1.0)
            bins vs1_0_neg_norm_big   = {64'hFFEF_FFFF_FFFF_FFFF}; // negative normal, large magnitude (near -max finite)

            bins vs1_0_pos_zero       = {64'h0000_0000_0000_0000}; // +0.0

            bins vs1_0_pos_sub_tiny   = {64'h0000_0000_0000_0001}; // positive subnormal, tiny magnitude
            bins vs1_0_pos_sub_big    = {64'h000F_FFFF_FFFF_FFFF}; // positive subnormal, larger magnitude

            bins vs1_0_pos_norm_small = {64'h3FF0_0000_0000_0000}; // positive normal, small magnitude (e.g., +1.0)
            bins vs1_0_pos_norm_big   = {64'h7FEF_FFFF_FFFF_FFFF}; // positive normal, large magnitude (near max finite)

            bins vs1_0_pos_inf        = {64'h7FF0_0000_0000_0000}; // +∞

            bins vs1_0_qNaN           = {64'h7FF8_0000_0000_0000}; // qNaN input (canonical)
            bins vs1_0_sNaN           = {64'h7FF0_0000_0000_0001}; // sNaN input (example)
        `endif
    }


    cp_custom_FpRecSqrtEst_flag_edges: cross std_vec, vs1_0_recip7_edges, fp_flags_clear;

    //// end cp_custom_FpRecipEst_flag_edges////////////////////////////////////////////////
