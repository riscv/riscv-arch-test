    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_subnorm_sew16
    //////////////////////////////////////////////////////////////////////////////////

    // vfrec7.v subnormal inputs and outputs at SEW=16. Overflowing subnormals are crossed with frm
    // and sign, because the result is inf or the greatest finite value depending on both.

    FpRecipEst_subnorm_vsew : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e16 = {1};
    }

    FpRecipEst_subnorm_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[15:0] {
        bins pos_sub_lz0      = {[16'h0200:16'h03FF]}; // normal result
        bins neg_sub_lz0      = {[16'h8200:16'h83FF]}; // normal result
        bins pos_sub_lz1      = {[16'h0100:16'h01FF]}; // normal result
        bins neg_sub_lz1      = {[16'h8100:16'h81FF]}; // normal result
        bins pos_norm_subres1 = {[16'h7400:16'h77FF]}; // subnormal result
        bins neg_norm_subres1 = {[16'hF400:16'hF7FF]}; // subnormal result
        bins pos_norm_subres2 = {[16'h7800:16'h7BFF]}; // subnormal result
        bins neg_norm_subres2 = {[16'hF800:16'hFBFF]}; // subnormal result
    }

    FpRecipEst_ovf_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[15:0] {
        bins pos_sub_ovf = {[16'h0001:16'h00FF]}; // +/-inf or +/-greatest finite by frm; OF, NX
        bins neg_sub_ovf = {[16'h8001:16'h80FF]}; // +/-inf or +/-greatest finite by frm; OF, NX
    }

    FpRecipEst_ovf_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm") {
        bins rne = {0};
        bins rtz = {1};
        bins rdn = {2};
        bins rup = {3};
        bins rmm = {4};
    }

    cp_custom_FpRecipEst_subnorm_sew16 : cross std_vec, FpRecipEst_subnorm_vsew, FpRecipEst_subnorm_vs2;
    cp_custom_FpRecipEst_subnorm_ovf_sew16 : cross std_vec, FpRecipEst_subnorm_vsew, FpRecipEst_ovf_vs2, FpRecipEst_ovf_frm;

    //// end cp_custom_FpRecipEst_subnorm_sew16 ////////////////////////////////////////////////
