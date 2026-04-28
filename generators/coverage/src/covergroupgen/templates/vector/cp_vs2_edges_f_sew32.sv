    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs2_edges_f_sew32
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs2_edges_f_sew32 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31:0]  iff (ins.trap == 0 )  {
        // Standard precision coverpoints
        bins pos0                   = {32'h00000000};
        bins neg0                   = {32'h80000000};
        bins pos1                   = {32'h3F800000};
        bins neg1                   = {32'hBF800000};
        bins posminnorm             = {32'h00800000};
        bins negmaxnorm             = {32'hFF7FFFFF};
        bins posinfinity            = {32'h7F800000};
        bins neginfinity            = {32'hFF800000};
        bins pos0p5                 = {32'h3F000000};
        bins pos1p5                 = {32'h3FC00000};
        bins neg2                   = {32'hC0000000};
        bins pi                     = {32'h40490FDB};
        bins twoToEmax              = {32'h7F000000};   // 2^127
        bins onePulp                = {32'h3F800001};   // 1 + ULP
        bins largestsubnorm         = {32'h007FFFFF};
        bins negSubnormLeadingOne   = {32'h80400000};   // subnormal with MSB of fraction = 1
        bins min_subnorm            = {32'h00000001};
        bins canonicalQNaN          = {32'h7FC00000};   // quiet NaN, canonical payload
        bins negNoncanonicalQNaN    = {[32'hFFC00001:32'hFFFFFFFF]}; // other quiet NaNs
        bins sNaN_payload1          = {32'h7F800001};   // signaling NaN with payload 1
    }

    //// end cp_vs2_edges_f_sew32         //////////////////////////////////////////////////
