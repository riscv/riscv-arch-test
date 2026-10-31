    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_subnorm_sew64
    //////////////////////////////////////////////////////////////////////////////////

    // vfrec7.v subnormal inputs and outputs at SEW=64. Overflowing subnormals are crossed with frm
    // and sign, because the result is inf or the greatest finite value depending on both.

    FpRecipEst_subnorm_vsew : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e64 = {3};
    }

    FpRecipEst_subnorm_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[63:0] {
        bins pos_sub_lz0      = {[64'h0008_0000_0000_0000:64'h000F_FFFF_FFFF_FFFF]}; // normal result
        bins neg_sub_lz0      = {[64'h8008_0000_0000_0000:64'h800F_FFFF_FFFF_FFFF]}; // normal result
        bins pos_sub_lz1      = {[64'h0004_0000_0000_0000:64'h0007_FFFF_FFFF_FFFF]}; // normal result
        bins neg_sub_lz1      = {[64'h8004_0000_0000_0000:64'h8007_FFFF_FFFF_FFFF]}; // normal result
        bins pos_norm_subres1 = {[64'h7FD0_0000_0000_0000:64'h7FDF_FFFF_FFFF_FFFF]}; // subnormal result
        bins neg_norm_subres1 = {[64'hFFD0_0000_0000_0000:64'hFFDF_FFFF_FFFF_FFFF]}; // subnormal result
        bins pos_norm_subres2 = {[64'h7FE0_0000_0000_0000:64'h7FEF_FFFF_FFFF_FFFF]}; // subnormal result
        bins neg_norm_subres2 = {[64'hFFE0_0000_0000_0000:64'hFFEF_FFFF_FFFF_FFFF]}; // subnormal result
    }

    FpRecipEst_ovf_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[63:0] {
        bins pos_sub_ovf = {[64'h0000_0000_0000_0001:64'h0003_FFFF_FFFF_FFFF]}; // +/-inf or +/-greatest finite by frm; OF, NX
        bins neg_sub_ovf = {[64'h8000_0000_0000_0001:64'h8003_FFFF_FFFF_FFFF]}; // +/-inf or +/-greatest finite by frm; OF, NX
    }

    FpRecipEst_ovf_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm") {
        bins rne = {0};
        bins rtz = {1};
        bins rdn = {2};
        bins rup = {3};
        bins rmm = {4};
    }

    cp_custom_FpRecipEst_subnorm_sew64 : cross std_vec, FpRecipEst_subnorm_vsew, FpRecipEst_subnorm_vs2;
    cp_custom_FpRecipEst_subnorm_ovf_sew64 : cross std_vec, FpRecipEst_subnorm_vsew, FpRecipEst_ovf_vs2, FpRecipEst_ovf_frm;

    //// end cp_custom_FpRecipEst_subnorm_sew64 ////////////////////////////////////////////////
