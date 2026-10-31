    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecSqrtEst_subnorm_sew16
    //////////////////////////////////////////////////////////////////////////////////

    // vfrsqrt7.v positive subnormal inputs at SEW=16. Each count of leading zeros takes a
    // different normalization shift.

    FpRecSqrtEst_subnorm_vsew : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e16 = {1};
    }

    FpRecSqrtEst_subnorm_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[15:0] {
        bins pos_sub_lz0 = {[16'h0200:16'h03FF]};
        bins pos_sub_lz1 = {[16'h0100:16'h01FF]};
        bins pos_sub_lz2 = {[16'h0080:16'h00FF]};
        bins pos_sub_lz3 = {[16'h0040:16'h007F]};
        bins pos_sub_lz4 = {[16'h0020:16'h003F]};
        bins pos_sub_lz5 = {[16'h0010:16'h001F]};
        bins pos_sub_lz6 = {[16'h0008:16'h000F]};
        bins pos_sub_lz7 = {[16'h0004:16'h0007]};
        bins pos_sub_lz8 = {[16'h0002:16'h0003]};
        bins pos_sub_lz9 = {16'h0001};
    }

    cp_custom_FpRecSqrtEst_subnorm_sew16 : cross std_vec, FpRecSqrtEst_subnorm_vsew, FpRecSqrtEst_subnorm_vs2;

    //// end cp_custom_FpRecSqrtEst_subnorm_sew16 ////////////////////////////////////////////////
