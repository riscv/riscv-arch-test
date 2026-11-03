    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_flag_edges
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0] {
            bins clear = {0};
    }

    vs2_0_recip7_edges : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
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

            // Rows of the spec's vfrec7 table that the bins above miss, where B is the exponent bias
            bins vs1_0_neg_sub_normres_min       = {64'h0000_0000_0000_8100}; // negative subnormal, x = -2^-(B+1), smallest magnitude in row -2^-B < x ≤ -2^-(B+1)
            bins vs1_0_neg_norm_subres_min       = {64'h0000_0000_0000_F400}; // negative normal, x = -2^(B-1), smallest magnitude in row -2^B < x ≤ -2^(B-1)
            bins vs1_0_pos_sub_normres_min       = {64'h0000_0000_0000_0100}; // positive subnormal, x = 2^-(B+1), smallest magnitude in row 2^-(B+1) ≤ x < 2^-B
            bins vs1_0_pos_norm_subres_min       = {64'h0000_0000_0000_7400}; // positive normal, x = 2^(B-1), smallest magnitude in row 2^(B-1) ≤ x < 2^B
        `elsif COVER_VFCUSTOM32
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

            // Rows of the spec's vfrec7 table that the bins above miss, where B is the exponent bias
            bins vs1_0_neg_sub_normres_min       = {64'h0000_0000_8020_0000}; // negative subnormal, x = -2^-(B+1), smallest magnitude in row -2^-B < x ≤ -2^-(B+1)
            bins vs1_0_neg_norm_subres_min       = {64'h0000_0000_FE80_0000}; // negative normal, x = -2^(B-1), smallest magnitude in row -2^B < x ≤ -2^(B-1)
            bins vs1_0_pos_sub_normres_min       = {64'h0000_0000_0020_0000}; // positive subnormal, x = 2^-(B+1), smallest magnitude in row 2^-(B+1) ≤ x < 2^-B
            bins vs1_0_pos_norm_subres_min       = {64'h0000_0000_7E80_0000}; // positive normal, x = 2^(B-1), smallest magnitude in row 2^(B-1) ≤ x < 2^B
        `endif
    }

    // Rows -2^-(B+1) < x < -0.0 and +0.0 < x < 2^-(B+1): the result is ±∞ or ±greatest finite depending on frm
    vs2_0_recip7_ovf : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        `ifdef COVER_VFCUSTOM16
            bins vs1_0_neg_sub_tiny = {64'h0000_0000_0000_8001}; // negative subnormal, tiny magnitude, in row -2^-(B+1) < x < -0.0
            bins vs1_0_pos_sub_tiny = {64'h0000_0000_0000_0001}; // positive subnormal, tiny magnitude, in row +0.0 < x < 2^-(B+1)
        `elsif COVER_VFCUSTOM32
            bins vs1_0_neg_sub_tiny = {64'h0000_0000_8000_0001}; // negative subnormal, tiny magnitude, in row -2^-(B+1) < x < -0.0
            bins vs1_0_pos_sub_tiny = {64'h0000_0000_0000_0001}; // positive subnormal, tiny magnitude, in row +0.0 < x < 2^-(B+1)
        `endif
    }

    vs2_0_recip7_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm") {
            bins rne = {0};
            bins rtz = {1};
            bins rdn = {2};
            bins rup = {3};
            bins rmm = {4};
    }

    cp_custom_FpRecipEst_flag_edges: cross std_vec, vs2_0_recip7_edges, fp_flags_clear;
    cp_custom_FpRecipEst_flag_edges_frm: cross std_vec, vs2_0_recip7_ovf, fp_flags_clear, vs2_0_recip7_frm;
`else
    `ifdef D_SUPPORTED
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

            // Rows of the spec's vfrec7 table that the bins above miss, where B is the exponent bias
            bins vs1_0_neg_sub_normres_min       = {64'h8004_0000_0000_0000}; // negative subnormal, x = -2^-(B+1), smallest magnitude in row -2^-B < x ≤ -2^-(B+1)
            bins vs1_0_neg_norm_subres_min       = {64'hFFD0_0000_0000_0000}; // negative normal, x = -2^(B-1), smallest magnitude in row -2^B < x ≤ -2^(B-1)
            bins vs1_0_pos_sub_normres_min       = {64'h0004_0000_0000_0000}; // positive subnormal, x = 2^-(B+1), smallest magnitude in row 2^-(B+1) ≤ x < 2^-B
            bins vs1_0_pos_norm_subres_min       = {64'h7FD0_0000_0000_0000}; // positive normal, x = 2^(B-1), smallest magnitude in row 2^(B-1) ≤ x < 2^B
    }

    // Rows -2^-(B+1) < x < -0.0 and +0.0 < x < 2^-(B+1): the result is ±∞ or ±greatest finite depending on frm
    vs2_0_recip7_ovf : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
            bins vs1_0_neg_sub_tiny = {64'h8000_0000_0000_0001}; // negative subnormal, tiny magnitude, in row -2^-(B+1) < x < -0.0
            bins vs1_0_pos_sub_tiny = {64'h0000_0000_0000_0001}; // positive subnormal, tiny magnitude, in row +0.0 < x < 2^-(B+1)
    }

    vs2_0_recip7_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm") {
            bins rne = {0};
            bins rtz = {1};
            bins rdn = {2};
            bins rup = {3};
            bins rmm = {4};
    }

    cp_custom_FpRecipEst_flag_edges: cross std_vec, vs2_0_recip7_edges, fp_flags_clear;
    cp_custom_FpRecipEst_flag_edges_frm: cross std_vec, vs2_0_recip7_ovf, fp_flags_clear, vs2_0_recip7_frm;
    `endif
`endif

    //// end cp_custom_FpRecipEst_flag_edges////////////////////////////////////////////////
