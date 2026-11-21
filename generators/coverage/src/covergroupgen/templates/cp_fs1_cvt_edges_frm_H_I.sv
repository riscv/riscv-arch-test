    cp_fs1_cvt_edges_H_I : coverpoint unsigned'(ins.current.fs1_val[15:0])  iff (ins.trap == 0 )  {
        // FS1 fractional values (the integer result depends on the rounding mode)
        bins pos1p75                  = {16'h3f00};
        bins neg0p5                   = {16'hb800};
    }

    cr_fs1_cvt_edges_frm_H_I : cross cp_fs1_cvt_edges_H_I,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
