// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_custom_vfncvt_rod_overflow
//
// Verifies normative statement: "For vfncvt.rod.f.f.w, a finite value that exceeds the range of the
// destination format is converted to the destination format's largest finite value with the same sign."
//
// Uses a 64-bit source value whose magnitude exceeds the largest finite 32-bit float (~3.4028235e+38)
// but is still a finite 64-bit double. Round-to-odd must NOT produce infinity; it must clamp to the
// largest finite FP32 value with the same sign.
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

`ifdef COVER_VFCUSTOM32
    // Standard vector preconditions: vill=0, vstart=0, vl!=0, no trap

    // SEW = 32 (destination is 32-bit single, source is 64-bit double)
    rod_vtype_sew_32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e32 = {2};
    }

    // Source element[0] is a finite value exceeding FP32 max range
    // FP32 max = 0x47EFFFFF_E0000000 in FP64 encoding (~3.4028235e+38)
    // Any finite FP64 with magnitude above that but below infinity triggers overflow on narrowing
    // NOTE: Cannot use get_vr_element_zero() here because it extracts based on
    // vsew (output SEW=32), but vs2 has 2*SEW=64-bit elements for narrowing ops.
    // Directly extract the lower 64 bits of vs2_val to get element 0 at double width.
    rod_vs2_exceeds_f32_range: coverpoint ins.current.vs2_val[63:0] {
        // Positive finite values exceeding FP32 max (exponent > 127 biased, i.e., FP64 biased exp >= 1151)
        bins pos_overflow = {[64'h47F0000000000000:64'h7FEFFFFFFFFFFFFF]};
        // Negative finite values exceeding FP32 max magnitude
        bins neg_overflow = {[64'hC7F0000000000000:64'hFFEFFFFFFFFFFFFF]};
    }

    cp_custom_vfncvt_rod_overflow: cross std_vec, rod_vtype_sew_32, rod_vs2_exceeds_f32_range;
`endif

//// end cp_custom_vfncvt_rod_overflow ///////////////////////////////////////////////////////////////////////////
