// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vstart_ge_vlmax
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vstart >= VLMAX is reserved (out of bounds for current vtype)
    vstart_ge_vlmax: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                                 get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins true = {1'b1};
    }

    vtype_valid_8f65a1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }

    cp_ssstrictv_vstart_ge_vlmax: cross vstart_ge_vlmax, vtype_valid_8f65a1;

//// end cp_ssstrictv_vstart_ge_vlmax ///////////////////////////////////////////////////////////////////
