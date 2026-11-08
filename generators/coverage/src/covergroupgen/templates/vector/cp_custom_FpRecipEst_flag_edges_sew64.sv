    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_flag_edges
    //////////////////////////////////////////////////////////////////////////////////

    fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0] {
        bins clear = {0};
    }

    vs2_0_recip7_edges : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
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
    }

    cp_custom_FpRecipEst_flag_edges: cross std_vec, vs2_0_recip7_edges, fp_flags_clear;

    //// end cp_custom_FpRecipEst_flag_edges////////////////////////////////////////////////
