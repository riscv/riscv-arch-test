    cp_fs1_cvt_edges_H_R : coverpoint unsigned'(ins.current.fs1_val[15:0])  iff (ins.trap == 0 )  {
        // FS1 values whose rounding to an integral value depends on the rounding mode
        bins pos2p5                   = {16'h4100};
        bins neg2p5                   = {16'hc100};
        bins pos1p75                  = {16'h3f00};
        bins neg0p5                   = {16'hb800};
        bins max_fraction             = {16'h63ff};
    }

    cr_fs1_cvt_edges_frm_H_R : cross cp_fs1_cvt_edges_H_R,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
