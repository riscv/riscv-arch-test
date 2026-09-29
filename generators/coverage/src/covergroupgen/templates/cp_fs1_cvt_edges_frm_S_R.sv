    cp_fs1_cvt_edges_S_R : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 values whose rounding to an integral value depends on the rounding mode
        bins pos2p5                   = {32'h40200000};
        bins neg2p5                   = {32'hc0200000};
        bins pos1p75                  = {32'h3fe00000};
        bins neg0p5                   = {32'hbf000000};
        bins max_fraction             = {32'h4affffff};
    }

    cr_fs1_cvt_edges_frm_S_R : cross cp_fs1_cvt_edges_S_R,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
