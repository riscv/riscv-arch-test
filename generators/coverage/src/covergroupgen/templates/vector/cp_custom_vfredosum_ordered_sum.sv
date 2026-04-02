// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_custom_vfredosum_ordered_sum
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    // Ordered sum cancellation: (maxNorm + (-maxNorm)) + small = small, not 0
    vs1_0_maxNorm : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val) {
        `ifdef COVER_VFCUSTOM16
        bins maxNorm = {64'h7BFF};
        `elsif COVER_VFCUSTOM32
        bins maxNorm = {64'h7F7FFFFF};
        `endif
    }

    vs2_0_neg_maxNorm : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        `ifdef COVER_VFCUSTOM16
        bins negMaxNorm = {64'hFBFF};
        `elsif COVER_VFCUSTOM32
        bins negMaxNorm = {64'hFF7FFFFF};
        `endif
    }

    vl_ge_2 : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") >= 2) {
        bins true = {1};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    cp_custom_vfredosum_ordered_sum : cross std_vec, vl_ge_2, vs1_0_maxNorm, vs2_0_neg_maxNorm, vtype_lmul_2 iff (ins.trap == 0);
`else
    `ifdef FLEN64
    // Ordered sum cancellation: (maxNorm + (-maxNorm)) + small = small, not 0
    vs1_0_maxNorm : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val) {
        bins maxNorm = {64'h7FEFFFFFFFFFFFFF};
    }

    vs2_0_neg_maxNorm : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        bins negMaxNorm = {64'hFFEFFFFFFFFFFFFF};
    }

    vl_ge_2 : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") >= 2) {
        bins true = {1};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    cp_custom_vfredosum_ordered_sum : cross std_vec, vl_ge_2, vs1_0_maxNorm, vs2_0_neg_maxNorm, vtype_lmul_2 iff (ins.trap == 0);
    `endif
`endif

//// end cp_custom_vfredosum_ordered_sum ///////////////////////////////////////////////////////////////////////////
