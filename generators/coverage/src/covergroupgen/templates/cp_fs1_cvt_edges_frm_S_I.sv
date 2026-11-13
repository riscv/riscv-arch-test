    cp_fs1_cvt_edges_S_I : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 fractional values (the integer result depends on the rounding mode)
        bins pos1p75                  = {32'h3fe00000};
        bins neg0p5                   = {32'hbf000000};
    }

    cp_fs1_cvt_exact_S_I : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 integers at the saturation boundaries of 32- and 64-bit destinations
        bins w_max_valid              = {32'h4effffff};
        bins w_pos_overflow           = {32'h4f000000};
        bins w_min                    = {32'hcf000000};
        bins w_neg_overflow           = {32'hcf000001};
        bins wu_max_valid             = {32'h4f7fffff};
        bins wu_overflow              = {32'h4f800000};
        bins l_max_valid              = {32'h5effffff};
        bins l_pos_overflow           = {32'h5f000000};
        bins l_min                    = {32'hdf000000};
        bins l_neg_overflow           = {32'hdf000001};
        bins lu_max_valid             = {32'h5f7fffff};
        bins lu_overflow              = {32'h5f800000};
    }

    cr_fs1_cvt_edges_frm_S_I : cross cp_fs1_cvt_edges_S_I,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
