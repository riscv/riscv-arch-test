    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfredusum_sweep
    // Unordered sum reductions checked against every legal tree: vl x frm x masking
    //////////////////////////////////////////////////////////////////////////////////

    vfredusum_sweep_vl : coverpoint vred_vl_class(ins.hart, ins.issue) {
        bins two   = {vred_vl_2};
        bins three = {vred_vl_3};
        bins four  = {vred_vl_4};
        bins seven = {vred_vl_7};
        bins vlmax = {vred_vl_vlmax};
    }

    vfredusum_sweep_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm") {
        bins rne = {3'b000};
        bins rtz = {3'b001};
        bins rdn = {3'b010};
        bins rup = {3'b011};
        bins rmm = {3'b100};
    }

    vfredusum_sweep_mask : coverpoint vred_mask_class(ins.hart, ins.issue, ins.current.vm, ins.prev.v_wdata[0]) {
        bins unmasked    = {vred_unmasked};
        bins some_active = {vred_some_active};
        bins none_active = {vred_none_active};
    }

    cp_custom_vfredusum_sweep : cross std_vec, vfredusum_sweep_vl, vfredusum_sweep_frm, vfredusum_sweep_mask iff (ins.trap == 0);

    //// end cp_custom_vfredusum_sweep ////////////////////////////////////////////////
