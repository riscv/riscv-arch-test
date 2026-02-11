// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_custom_vfredosum_ordered_sum
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Ordered sum cancellation: (maxNorm + (-maxNorm)) + small = small, not 0
    vs1_0_maxNorm : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val) {
        `ifdef SEW16_SUPPORTED
        bins maxNorm = {64'h7BFF};
        `endif
        `ifdef SEW32_SUPPORTED
        bins maxNorm = {64'h7F7FFFFF};
        `endif
        `ifdef SEW64_SUPPORTED
        bins maxNorm = {64'h7FEFFFFFFFFFFFFF};
        `endif
    }

    vs2_0_neg_maxNorm : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        `ifdef SEW16_SUPPORTED
        bins negMaxNorm = {64'hFBFF};
        `endif
        `ifdef SEW32_SUPPORTED
        bins negMaxNorm = {64'hFF7FFFFF};
        `endif
        `ifdef SEW64_SUPPORTED
        bins negMaxNorm = {64'hFFEFFFFFFFFFFFFF};
        `endif
    }

    vl_ge_2 : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") >= 2) {
        bins true = {1};
    }

    cp_custom_vfredosum_ordered_sum : cross std_vec, vl_ge_2, vs1_0_maxNorm, vs2_0_neg_maxNorm, vtype_lmul_2 iff (ins.trap == 0);

//// end cp_custom_vfredosum_ordered_sum ///////////////////////////////////////////////////////////////////////////
