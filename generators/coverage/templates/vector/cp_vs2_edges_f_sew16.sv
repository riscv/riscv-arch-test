//////////////////////////////////////////////////////////////////////////////////
    // cp_vs2_edges_f_sew16
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs2_edges_f_sew16 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[15:0]  iff (ins.trap == 0 )  {
        // (Half Precision)
        bins pos0                   = {16'h0000};
        bins neg0                   = {16'h8000};
        bins pos1                   = {16'h3C00};
        bins neg1                   = {16'hBC00};
        bins posminnorm             = {16'h0400};
        bins negmaxnorm             = {16'hFBFF};
        bins posinfinity            = {16'h7C00};
        bins neginfinity            = {16'hFC00};
        bins pos0p5                 = {16'h3800};
        bins pos1p5                 = {16'h3E00};
        bins neg2                   = {16'hC000};
        bins pi                     = {16'h4248};
        bins twoToEmax              = {16'h7800};
        bins onePulp                = {16'h3c01};
        bins largestsubnorm         = {16'h03FF};
        bins negSubnormLeadingOne   = {16'h8200};
        bins min_subnorm            = {16'h0001};
        bins canonicalQNaN          = {16'h7E00};                // Quiet NaN with only MSB of fraction set
        bins negNoncanonicalQNaN    = {[16'hFE01:16'hFFFF]};     // Quiet NaNs excluding canonical
        bins sNaN_payload1          = {16'h7D01};                // Signaling NaN with payload 1
    }

    //// end cp_vs2_edges_f_sew16////////////////////////////////////////////////
