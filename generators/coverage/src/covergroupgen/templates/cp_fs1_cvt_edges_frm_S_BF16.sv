    cp_fs1_cvt_edges_S_BF16 : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 values near the destination's rounding, overflow and underflow boundaries
        bins posmax_half_ulp          = {32'h7f7f8000};
        bins negmax_half_ulp          = {32'hff7f8000};
        bins tiny_before_rounding     = {32'h007fc000};
        bins posmin_subnorm_half      = {32'h00008000};
        bins negmin_subnorm_half      = {32'h80008000};
        bins pos1_half_ulp            = {32'h3f808000};
        bins neg1_half_ulp            = {32'hbf808000};
        bins pos1_3half_ulp           = {32'h3f818000};
    }

    cp_fs1_cvt_exact_S_BF16 : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 destination max, minnorm and min subnormal, exactly representable
        bins posmaxnorm               = {32'h7f7f0000};
        bins posminnorm               = {32'h00800000};
        bins posmin_subnorm           = {32'h00010000};
    }

    cr_fs1_cvt_edges_frm_S_BF16 : cross cp_fs1_cvt_edges_S_BF16,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
