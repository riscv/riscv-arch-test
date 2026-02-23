//////////////////////////////////////////////////////////////////////////////////
    // cp_vs2_edges_f_sew64
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs2_edges_f_sew64 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[63:0]  iff (ins.trap == 0 )  {
        // (Double Precision)
        bins pos0                   = {64'h0000000000000000};
        bins neg0                   = {64'h8000000000000000};
        bins pos1                   = {64'h3FF0000000000000};
        bins neg1                   = {64'hBFF0000000000000};
        bins posminnorm             = {64'h0010000000000000};
        bins negmaxnorm             = {64'hFFEFFFFFFFFFFFFF};
        bins posinfinity            = {64'h7FF0000000000000};
        bins neginfinity            = {64'hFFF0000000000000};
        bins pos0p5                 = {64'h3FE0000000000000};
        bins pos1p5                 = {64'h3FF8000000000000};
        bins neg2                   = {64'hC000000000000000};
        bins pi                     = {64'h400921FB54442D18};
        bins twoToEmax              = {64'h7FE0000000000000};   // 2^1023
        bins onePulp                = {64'h3FF0000000000001};   // 1 + ULP
        bins largestsubnorm         = {64'h000FFFFFFFFFFFFF};
        bins negSubnormLeadingOne   = {64'h8008000000000000};
        bins min_subnorm            = {64'h0000000000000001};
        bins canonicalQNaN          = {64'h7FF8000000000000};   // quiet NaN, canonical payload
        bins negNoncanonicalQNaN    = {[64'hFFF8000000000001:64'hFFFFFFFFFFFFFFFF]}; // other quiet NaNs
        bins sNaN_payload1          = {64'h7FF0000000000001};   // signaling NaN with payload 1
    }

    //// end cp_vs2_edges_f_sew64////////////////////////////////////////////////
