    cp_rs1_cvt_edges_W_S : coverpoint unsigned'(ins.current.rs1_val[31:0])  iff (ins.trap == 0 )  {
        // RS1 integers whose conversion depends on the rounding mode
        bins tie_even_down            = {32'h01000001};
        bins tie_even_up              = {32'h01000003};
        bins neg_tie                  = {32'hfeffffff};
        bins below_tie                = {32'h02000001};
        bins sticky                   = {32'h40000041};
        bins carry_max                = {32'h7fffffc0};
        bins carry_umax               = {32'hffffff80};
        bins min                      = {32'h80000000};
        bins max                      = {32'h7fffffff};
    }

    cr_rs1_cvt_edges_frm_W_S : cross cp_rs1_cvt_edges_W_S,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage RS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
