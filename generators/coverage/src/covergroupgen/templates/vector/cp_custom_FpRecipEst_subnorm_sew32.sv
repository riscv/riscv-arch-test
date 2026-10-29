    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_subnorm_sew32
    //////////////////////////////////////////////////////////////////////////////////

    // vfrec7.v subnormal inputs and outputs at SEW=32. Overflowing subnormals are crossed with frm
    // and sign, because the result is inf or the greatest finite value depending on both.

    FpRecipEst_subnorm_vsew : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e32 = {2};
    }

    FpRecipEst_subnorm_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31:0] {
        bins pos_sub_lz0      = {[32'h0040_0000:32'h007F_FFFF]}; // normal result
        bins neg_sub_lz0      = {[32'h8040_0000:32'h807F_FFFF]}; // normal result
        bins pos_sub_lz1      = {[32'h0020_0000:32'h003F_FFFF]}; // normal result
        bins neg_sub_lz1      = {[32'h8020_0000:32'h803F_FFFF]}; // normal result
        bins pos_norm_subres1 = {[32'h7E80_0000:32'h7EFF_FFFF]}; // subnormal result
        bins neg_norm_subres1 = {[32'hFE80_0000:32'hFEFF_FFFF]}; // subnormal result
        bins pos_norm_subres2 = {[32'h7F00_0000:32'h7F7F_FFFF]}; // subnormal result
        bins neg_norm_subres2 = {[32'hFF00_0000:32'hFF7F_FFFF]}; // subnormal result
    }

    FpRecipEst_ovf_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31:0] {
        bins pos_sub_ovf = {[32'h0000_0001:32'h001F_FFFF]}; // +/-inf or +/-greatest finite by frm; OF, NX
        bins neg_sub_ovf = {[32'h8000_0001:32'h801F_FFFF]}; // +/-inf or +/-greatest finite by frm; OF, NX
    }

    FpRecipEst_ovf_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm") {
        bins rne = {0};
        bins rtz = {1};
        bins rdn = {2};
        bins rup = {3};
        bins rmm = {4};
    }

    cp_custom_FpRecipEst_subnorm_sew32 : cross std_vec, FpRecipEst_subnorm_vsew, FpRecipEst_subnorm_vs2;
    cp_custom_FpRecipEst_subnorm_ovf_sew32 : cross std_vec, FpRecipEst_subnorm_vsew, FpRecipEst_ovf_vs2, FpRecipEst_ovf_frm;

    //// end cp_custom_FpRecipEst_subnorm_sew32 ////////////////////////////////////////////////
