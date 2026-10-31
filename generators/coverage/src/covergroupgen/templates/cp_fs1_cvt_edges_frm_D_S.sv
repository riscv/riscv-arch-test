    cp_fs1_cvt_edges_D_S : coverpoint unsigned'(ins.current.fs1_val[63:0])  iff (ins.trap == 0 )  {
        // FS1 values near the destination's rounding, overflow and underflow boundaries
        bins posmax_half_ulp          = {64'h47effffff0000000};
        bins negmax_half_ulp          = {64'hc7effffff0000000};
        bins tiny_before_rounding     = {64'h380ffffff0000000};
        bins posmin_subnorm_half      = {64'h3690000000000000};
        bins negmin_subnorm_half      = {64'hb690000000000000};
        bins pos1_half_ulp            = {64'h3ff0000010000000};
        bins neg1_half_ulp            = {64'hbff0000010000000};
        bins pos1_3half_ulp           = {64'h3ff0000030000000};
    }

    cp_fs1_cvt_exact_D_S : coverpoint unsigned'(ins.current.fs1_val[63:0])  iff (ins.trap == 0 )  {
        // FS1 destination max, minnorm and min subnormal, exactly representable
        bins posmaxnorm               = {64'h47efffffe0000000};
        bins posminnorm               = {64'h3810000000000000};
        bins posmin_subnorm           = {64'h36a0000000000000};
    }

    cr_fs1_cvt_edges_frm_D_S : cross cp_fs1_cvt_edges_D_S,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
