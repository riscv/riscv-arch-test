    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfncvt_rod_overflow
    //
    // Verifies normative statement: "For vfncvt.rod.f.f.w, a finite value that exceeds the range of the
    // destination format is converted to the destination format's largest finite value with the same sign."
    //
    // Source element 0 is a finite FP64 value with magnitude >= 2^128, above the largest finite FP32 value.
    // Round-to-odd must clamp to the largest finite FP32 value with the same sign, not produce infinity.
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    rod_vs2_exceeds_f32_range: coverpoint get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs2_val) {
        bins pos_overflow = {[64'h47F0_0000_0000_0000:64'h7FEF_FFFF_FFFF_FFFF]};
        bins neg_overflow = {[64'hC7F0_0000_0000_0000:64'hFFEF_FFFF_FFFF_FFFF]};
    }

    cp_custom_vfncvt_rod_overflow: cross std_vec, rod_vs2_exceeds_f32_range;

//// end cp_custom_vfncvt_rod_overflow ///////////////////////////////////////////////////////////////////////////
