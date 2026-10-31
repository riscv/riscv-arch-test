    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecSqrtEst_subnorm_sew64
    //////////////////////////////////////////////////////////////////////////////////

    // vfrsqrt7.v positive subnormal inputs at SEW=64. Each count of leading zeros takes a
    // different normalization shift.

    FpRecSqrtEst_subnorm_vsew : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e64 = {3};
    }

    FpRecSqrtEst_subnorm_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[63:0] {
        bins pos_sub_lz0  = {[64'h0008_0000_0000_0000:64'h000F_FFFF_FFFF_FFFF]};
        bins pos_sub_lz1  = {[64'h0004_0000_0000_0000:64'h0007_FFFF_FFFF_FFFF]};
        bins pos_sub_lz2  = {[64'h0002_0000_0000_0000:64'h0003_FFFF_FFFF_FFFF]};
        bins pos_sub_lz3  = {[64'h0001_0000_0000_0000:64'h0001_FFFF_FFFF_FFFF]};
        bins pos_sub_lz4  = {[64'h0000_8000_0000_0000:64'h0000_FFFF_FFFF_FFFF]};
        bins pos_sub_lz5  = {[64'h0000_4000_0000_0000:64'h0000_7FFF_FFFF_FFFF]};
        bins pos_sub_lz6  = {[64'h0000_2000_0000_0000:64'h0000_3FFF_FFFF_FFFF]};
        bins pos_sub_lz7  = {[64'h0000_1000_0000_0000:64'h0000_1FFF_FFFF_FFFF]};
        bins pos_sub_lz8  = {[64'h0000_0800_0000_0000:64'h0000_0FFF_FFFF_FFFF]};
        bins pos_sub_lz9  = {[64'h0000_0400_0000_0000:64'h0000_07FF_FFFF_FFFF]};
        bins pos_sub_lz10 = {[64'h0000_0200_0000_0000:64'h0000_03FF_FFFF_FFFF]};
        bins pos_sub_lz11 = {[64'h0000_0100_0000_0000:64'h0000_01FF_FFFF_FFFF]};
        bins pos_sub_lz12 = {[64'h0000_0080_0000_0000:64'h0000_00FF_FFFF_FFFF]};
        bins pos_sub_lz13 = {[64'h0000_0040_0000_0000:64'h0000_007F_FFFF_FFFF]};
        bins pos_sub_lz14 = {[64'h0000_0020_0000_0000:64'h0000_003F_FFFF_FFFF]};
        bins pos_sub_lz15 = {[64'h0000_0010_0000_0000:64'h0000_001F_FFFF_FFFF]};
        bins pos_sub_lz16 = {[64'h0000_0008_0000_0000:64'h0000_000F_FFFF_FFFF]};
        bins pos_sub_lz17 = {[64'h0000_0004_0000_0000:64'h0000_0007_FFFF_FFFF]};
        bins pos_sub_lz18 = {[64'h0000_0002_0000_0000:64'h0000_0003_FFFF_FFFF]};
        bins pos_sub_lz19 = {[64'h0000_0001_0000_0000:64'h0000_0001_FFFF_FFFF]};
        bins pos_sub_lz20 = {[64'h0000_0000_8000_0000:64'h0000_0000_FFFF_FFFF]};
        bins pos_sub_lz21 = {[64'h0000_0000_4000_0000:64'h0000_0000_7FFF_FFFF]};
        bins pos_sub_lz22 = {[64'h0000_0000_2000_0000:64'h0000_0000_3FFF_FFFF]};
        bins pos_sub_lz23 = {[64'h0000_0000_1000_0000:64'h0000_0000_1FFF_FFFF]};
        bins pos_sub_lz24 = {[64'h0000_0000_0800_0000:64'h0000_0000_0FFF_FFFF]};
        bins pos_sub_lz25 = {[64'h0000_0000_0400_0000:64'h0000_0000_07FF_FFFF]};
        bins pos_sub_lz26 = {[64'h0000_0000_0200_0000:64'h0000_0000_03FF_FFFF]};
        bins pos_sub_lz27 = {[64'h0000_0000_0100_0000:64'h0000_0000_01FF_FFFF]};
        bins pos_sub_lz28 = {[64'h0000_0000_0080_0000:64'h0000_0000_00FF_FFFF]};
        bins pos_sub_lz29 = {[64'h0000_0000_0040_0000:64'h0000_0000_007F_FFFF]};
        bins pos_sub_lz30 = {[64'h0000_0000_0020_0000:64'h0000_0000_003F_FFFF]};
        bins pos_sub_lz31 = {[64'h0000_0000_0010_0000:64'h0000_0000_001F_FFFF]};
        bins pos_sub_lz32 = {[64'h0000_0000_0008_0000:64'h0000_0000_000F_FFFF]};
        bins pos_sub_lz33 = {[64'h0000_0000_0004_0000:64'h0000_0000_0007_FFFF]};
        bins pos_sub_lz34 = {[64'h0000_0000_0002_0000:64'h0000_0000_0003_FFFF]};
        bins pos_sub_lz35 = {[64'h0000_0000_0001_0000:64'h0000_0000_0001_FFFF]};
        bins pos_sub_lz36 = {[64'h0000_0000_0000_8000:64'h0000_0000_0000_FFFF]};
        bins pos_sub_lz37 = {[64'h0000_0000_0000_4000:64'h0000_0000_0000_7FFF]};
        bins pos_sub_lz38 = {[64'h0000_0000_0000_2000:64'h0000_0000_0000_3FFF]};
        bins pos_sub_lz39 = {[64'h0000_0000_0000_1000:64'h0000_0000_0000_1FFF]};
        bins pos_sub_lz40 = {[64'h0000_0000_0000_0800:64'h0000_0000_0000_0FFF]};
        bins pos_sub_lz41 = {[64'h0000_0000_0000_0400:64'h0000_0000_0000_07FF]};
        bins pos_sub_lz42 = {[64'h0000_0000_0000_0200:64'h0000_0000_0000_03FF]};
        bins pos_sub_lz43 = {[64'h0000_0000_0000_0100:64'h0000_0000_0000_01FF]};
        bins pos_sub_lz44 = {[64'h0000_0000_0000_0080:64'h0000_0000_0000_00FF]};
        bins pos_sub_lz45 = {[64'h0000_0000_0000_0040:64'h0000_0000_0000_007F]};
        bins pos_sub_lz46 = {[64'h0000_0000_0000_0020:64'h0000_0000_0000_003F]};
        bins pos_sub_lz47 = {[64'h0000_0000_0000_0010:64'h0000_0000_0000_001F]};
        bins pos_sub_lz48 = {[64'h0000_0000_0000_0008:64'h0000_0000_0000_000F]};
        bins pos_sub_lz49 = {[64'h0000_0000_0000_0004:64'h0000_0000_0000_0007]};
        bins pos_sub_lz50 = {[64'h0000_0000_0000_0002:64'h0000_0000_0000_0003]};
        bins pos_sub_lz51 = {64'h0000_0000_0000_0001};
    }

    cp_custom_FpRecSqrtEst_subnorm_sew64 : cross std_vec, FpRecSqrtEst_subnorm_vsew, FpRecSqrtEst_subnorm_vs2;

    //// end cp_custom_FpRecSqrtEst_subnorm_sew64 ////////////////////////////////////////////////
