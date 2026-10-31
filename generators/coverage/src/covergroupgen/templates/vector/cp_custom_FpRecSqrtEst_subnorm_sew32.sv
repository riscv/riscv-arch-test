    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecSqrtEst_subnorm_sew32
    //////////////////////////////////////////////////////////////////////////////////

    // vfrsqrt7.v positive subnormal inputs at SEW=32. Each count of leading zeros takes a
    // different normalization shift.

    FpRecSqrtEst_subnorm_vsew : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e32 = {2};
    }

    FpRecSqrtEst_subnorm_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31:0] {
        bins pos_sub_lz0  = {[32'h0040_0000:32'h007F_FFFF]};
        bins pos_sub_lz1  = {[32'h0020_0000:32'h003F_FFFF]};
        bins pos_sub_lz2  = {[32'h0010_0000:32'h001F_FFFF]};
        bins pos_sub_lz3  = {[32'h0008_0000:32'h000F_FFFF]};
        bins pos_sub_lz4  = {[32'h0004_0000:32'h0007_FFFF]};
        bins pos_sub_lz5  = {[32'h0002_0000:32'h0003_FFFF]};
        bins pos_sub_lz6  = {[32'h0001_0000:32'h0001_FFFF]};
        bins pos_sub_lz7  = {[32'h0000_8000:32'h0000_FFFF]};
        bins pos_sub_lz8  = {[32'h0000_4000:32'h0000_7FFF]};
        bins pos_sub_lz9  = {[32'h0000_2000:32'h0000_3FFF]};
        bins pos_sub_lz10 = {[32'h0000_1000:32'h0000_1FFF]};
        bins pos_sub_lz11 = {[32'h0000_0800:32'h0000_0FFF]};
        bins pos_sub_lz12 = {[32'h0000_0400:32'h0000_07FF]};
        bins pos_sub_lz13 = {[32'h0000_0200:32'h0000_03FF]};
        bins pos_sub_lz14 = {[32'h0000_0100:32'h0000_01FF]};
        bins pos_sub_lz15 = {[32'h0000_0080:32'h0000_00FF]};
        bins pos_sub_lz16 = {[32'h0000_0040:32'h0000_007F]};
        bins pos_sub_lz17 = {[32'h0000_0020:32'h0000_003F]};
        bins pos_sub_lz18 = {[32'h0000_0010:32'h0000_001F]};
        bins pos_sub_lz19 = {[32'h0000_0008:32'h0000_000F]};
        bins pos_sub_lz20 = {[32'h0000_0004:32'h0000_0007]};
        bins pos_sub_lz21 = {[32'h0000_0002:32'h0000_0003]};
        bins pos_sub_lz22 = {32'h0000_0001};
    }

    cp_custom_FpRecSqrtEst_subnorm_sew32 : cross std_vec, FpRecSqrtEst_subnorm_vsew, FpRecSqrtEst_subnorm_vs2;

    //// end cp_custom_FpRecSqrtEst_subnorm_sew32 ////////////////////////////////////////////////
