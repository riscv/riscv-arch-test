    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfredusum_specials_w
    // Unordered sum reductions of special values: class of vs1[0] (vs1 at 2*SEW) x class of vs2[0], vl = 2 to 4
    //////////////////////////////////////////////////////////////////////////////////

    vfredusum_specials_vs1 : coverpoint vred_fp_class(get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs1_val), 2 * vred_sew(ins.hart, ins.issue)) {
        bins pos0           = {vred_pos0};
        bins neg0           = {vred_neg0};
        bins posinf         = {vred_posinf};
        bins qnan           = {vred_qnan};
        bins snan           = {vred_snan};
        bins posmax         = {vred_posmax};
        bins negmax         = {vred_negmax};
        bins minsub         = {vred_minsub};
    }

    vfredusum_specials_vs2 : coverpoint vred_fp_class(get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val), vred_sew(ins.hart, ins.issue)) {
        bins pos0           = {vred_pos0};
        bins neg0           = {vred_neg0};
        bins posinf         = {vred_posinf};
        bins qnan           = {vred_qnan};
        bins snan           = {vred_snan};
        bins posmax         = {vred_posmax};
        bins negmax         = {vred_negmax};
        bins minsub         = {vred_minsub};
        bins onepulp        = {vred_onepulp};
    }

    vfredusum_specials_vl : coverpoint vred_vl_class(ins.hart, ins.issue) {
        bins two_to_four = {vred_vl_2, vred_vl_3, vred_vl_4};
    }

    vfredusum_specials_unmasked : coverpoint ins.current.vm {
        bins unmasked = {1'b1};
    }

    cp_custom_vfredusum_specials_w : cross std_vec, vfredusum_specials_vs1, vfredusum_specials_vs2, vfredusum_specials_vl, vfredusum_specials_unmasked iff (ins.trap == 0);

    //// end cp_custom_vfredusum_specials_w ////////////////////////////////////////////////
