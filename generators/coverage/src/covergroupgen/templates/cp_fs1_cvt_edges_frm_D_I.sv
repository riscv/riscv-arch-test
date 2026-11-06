    cp_fs1_cvt_edges_D_I : coverpoint unsigned'(ins.current.fs1_val[63:0])  iff (ins.trap == 0 )  {
        // FS1 fractional values (the integer result depends on the rounding mode)
        bins pos1p75                  = {64'h3ffc000000000000};
        bins neg0p5                   = {64'hbfe0000000000000};
        bins w_max_tie                = {64'h41dfffffffe00000};
        bins w_min_tie                = {64'hc1e0000000100000};
        bins wu_max_tie               = {64'h41effffffff00000};
    }

    cp_fs1_cvt_exact_D_I : coverpoint unsigned'(ins.current.fs1_val[63:0])  iff (ins.trap == 0 )  {
        // FS1 integers at the saturation boundaries of 32- and 64-bit destinations
        bins w_pos_overflow           = {64'h41e0000000000000};
        bins w_min                    = {64'hc1e0000000000000};
        bins wu_overflow              = {64'h41f0000000000000};
        bins l_max_valid              = {64'h43dfffffffffffff};
        bins l_pos_overflow           = {64'h43e0000000000000};
        bins l_min                    = {64'hc3e0000000000000};
        bins l_neg_overflow           = {64'hc3e0000000000001};
        bins lu_max_valid             = {64'h43efffffffffffff};
        bins lu_overflow              = {64'h43f0000000000000};
    }

    cr_fs1_cvt_edges_frm_D_I : cross cp_fs1_cvt_edges_D_I,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
