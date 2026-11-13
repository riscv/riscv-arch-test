    cp_fs1_cvt_edges_D_R : coverpoint unsigned'(ins.current.fs1_val[63:0])  iff (ins.trap == 0 )  {
        // FS1 values whose rounding to an integral value depends on the rounding mode
        bins pos2p5                   = {64'h4004000000000000};
        bins neg2p5                   = {64'hc004000000000000};
        bins pos1p75                  = {64'h3ffc000000000000};
        bins neg0p5                   = {64'hbfe0000000000000};
        bins max_fraction             = {64'h432fffffffffffff};
    }

    cr_fs1_cvt_edges_frm_D_R : cross cp_fs1_cvt_edges_D_R,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
