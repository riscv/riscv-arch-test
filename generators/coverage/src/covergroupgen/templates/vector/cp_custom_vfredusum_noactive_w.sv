    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfredusum_noactive_w
    // Unordered sum reductions with no active elements: class of vs1[0] (vs1 at 2*SEW) x frm
    //////////////////////////////////////////////////////////////////////////////////

    vfredusum_noactive_vs1 : coverpoint vred_fp_class(get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs1_val), 2 * vred_sew(ins.hart, ins.issue)) {
        bins pos0           = {vred_pos0};
        bins neg0           = {vred_neg0};
        bins posinf         = {vred_posinf};
        bins neginf         = {vred_neginf};
        bins qnan           = {vred_qnan};
        bins qnan_other     = {vred_qnan_other};
        bins snan           = {vred_snan};
        bins posmax         = {vred_posmax};
        bins negmax         = {vred_negmax};
        bins minsub         = {vred_minsub};
        bins neg1           = {vred_neg1};
        bins onepulp        = {vred_onepulp};
    }

    vfredusum_noactive_mask : coverpoint vred_mask_class(ins.hart, ins.issue, ins.current.vm, ins.prev.v_wdata[0]) {
        bins none_active = {vred_none_active};
    }

    vfredusum_noactive_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm") {
        bins rne = {3'b000};
        bins rdn = {3'b010};
    }

    cp_custom_vfredusum_noactive_w : cross std_vec, vfredusum_noactive_vs1, vfredusum_noactive_mask, vfredusum_noactive_frm iff (ins.trap == 0);

    //// end cp_custom_vfredusum_noactive_w ////////////////////////////////////////////////
