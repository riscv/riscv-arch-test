    cp_fs1_cvt_edges_S_H : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 values near the destination's rounding, overflow and underflow boundaries
        bins posmax_half_ulp          = {32'h477ff000};
        bins negmax_half_ulp          = {32'hc77ff000};
        bins tiny_before_rounding     = {32'h387ff000};
        bins posmin_subnorm_half      = {32'h33000000};
        bins negmin_subnorm_half      = {32'hb3000000};
        bins pos1_half_ulp            = {32'h3f801000};
        bins neg1_half_ulp            = {32'hbf801000};
        bins pos1_3half_ulp           = {32'h3f803000};
    }

    cp_fs1_cvt_exact_S_H : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 destination max, minnorm and min subnormal, exactly representable
        bins posmaxnorm               = {32'h477fe000};
        bins posminnorm               = {32'h38800000};
        bins posmin_subnorm           = {32'h33800000};
    }

    cr_fs1_cvt_edges_frm_S_H : cross cp_fs1_cvt_edges_S_H,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
