    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfredusum_specials_sew64
    // Unordered sum reductions of special values (vs1 at SEW): vs1[0] x vs2[0], vl = 2 to 4
    //////////////////////////////////////////////////////////////////////////////////

    vfredusum_specials_vs1 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)[63:0] {
        bins pos0     = {64'h0000000000000000};   // +0
        bins neg0     = {64'h8000000000000000};   // -0
        bins posinf   = {64'h7FF0000000000000};   // +inf
        bins qnan     = {64'h7FF8000000000000};   // canonical quiet NaN
        bins snan     = {64'h7FF0000000000001};   // signaling NaN
        bins posmax   = {64'h7FEFFFFFFFFFFFFF};   // +largest finite
        bins negmax   = {64'hFFEFFFFFFFFFFFFF};   // -largest finite
        bins minsub   = {64'h0000000000000001};   // smallest positive subnormal
    }

    vfredusum_specials_vs2 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[63:0] {
        bins posinf   = {64'h7FF0000000000000};   // +inf
        bins posmax   = {64'h7FEFFFFFFFFFFFFF};   // +largest finite
        bins negmax   = {64'hFFEFFFFFFFFFFFFF};   // -largest finite
        bins qnan     = {64'h7FF8000000000000};   // canonical quiet NaN
        bins snan     = {64'h7FF0000000000001};   // signaling NaN
        bins neg0     = {64'h8000000000000000};   // -0
        bins pos0     = {64'h0000000000000000};   // +0
        bins minsub   = {64'h0000000000000001};   // smallest positive subnormal
        bins onepulp  = {64'h3FF0000000000001};   // 1 + ulp
    }

    vfredusum_specials_vl : coverpoint vred_vl_class(ins.hart, ins.issue) {
        bins two_to_four = {vred_vl_2, vred_vl_3, vred_vl_4};
    }

    vfredusum_specials_unmasked : coverpoint ins.current.vm {
        bins unmasked = {1'b1};
    }

    cp_custom_vfredusum_specials_sew64 : cross std_vec, vfredusum_specials_vs1, vfredusum_specials_vs2, vfredusum_specials_vl, vfredusum_specials_unmasked iff (ins.trap == 0);

    //// end cp_custom_vfredusum_specials_sew64 ////////////////////////////////////////////////
