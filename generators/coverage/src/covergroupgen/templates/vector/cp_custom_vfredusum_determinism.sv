    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfredusum_determinism
    // Unordered sum reductions repeated with scaled and negated data: vl x frm, unmasked
    //////////////////////////////////////////////////////////////////////////////////

    vfredusum_det_vl : coverpoint vred_vl_class(ins.hart, ins.issue) {
        bins three = {vred_vl_3};
        bins seven = {vred_vl_7};
        bins vlmax = {vred_vl_vlmax};
    }

    vfredusum_det_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm") {
        bins rne = {3'b000};
        bins rdn = {3'b010};
        bins rup = {3'b011};
    }

    vfredusum_det_unmasked : coverpoint ins.current.vm {
        bins unmasked = {1'b1};
    }

    cp_custom_vfredusum_determinism : cross std_vec, vfredusum_det_vl, vfredusum_det_frm, vfredusum_det_unmasked iff (ins.trap == 0);

    //// end cp_custom_vfredusum_determinism ////////////////////////////////////////////////
