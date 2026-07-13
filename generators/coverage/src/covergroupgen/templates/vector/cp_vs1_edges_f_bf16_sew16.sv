    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs1_edges_f_sew16
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs1_edges_f_bf16_sew16 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)[15:0]  iff (ins.trap == 0 )  {
        // (BF16 Precision)
        bins pos0                   = {16'h0000};
        bins neg0                   = {16'h8000};
        bins pos1                   = {16'h3F80};
        bins neg1                   = {16'hBF80};
        bins posminnorm             = {16'h0080};
        bins negmaxnorm             = {16'hFF7F};
        bins posinfinity            = {16'h7F80};
        bins neginfinity            = {16'hFF80};
        bins pos0p5                 = {16'h3f00};
        bins pos1p5                 = {16'h3FC0};
        bins neg2                   = {16'hC000};
        bins pi                     = {16'h4049};
        bins twoToEmax              = {16'h7f00};
        bins onePulp                = {16'h3f81};
        bins largestsubnorm         = {16'h007F};
        bins negSubnormLeadingOne   = {16'h8040};
        bins min_subnorm            = {16'h0001};
        bins canonicalQNaN          = {16'h7FC0};                // Quiet NaN with only MSB of fraction set
        bins negNoncanonicalQNaN    = {[16'hFFC1:16'hFFFF]};     // Quiet NaNs excluding canonical
        bins sNaN_payload1          = {16'h7F81};                // Signaling NaN with payload 1
    }

    //// end cp_vs1_edges_f_sew16////////////////////////////////////////////////
