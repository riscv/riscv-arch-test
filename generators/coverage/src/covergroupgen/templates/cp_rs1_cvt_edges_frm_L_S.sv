    cp_rs1_cvt_edges_L_S : coverpoint unsigned'(ins.current.rs1_val[63:0])  iff (ins.trap == 0 )  {
        // RS1 integers whose conversion depends on the rounding mode
        bins tie_even_down            = {64'h0000000001000001};
        bins tie_even_up              = {64'h0000000001000003};
        bins neg_tie                  = {64'hfffffffffeffffff};
        bins below_tie                = {64'h0000000002000001};
        bins sticky                   = {64'h0000010000010001};
        bins carry_max                = {64'h7fffffc000000000};
        bins carry_umax               = {64'hffffff8000000000};
        bins min                      = {64'h8000000000000000};
        bins max                      = {64'h7fffffffffffffff};
    }

    cr_rs1_cvt_edges_frm_L_S : cross cp_rs1_cvt_edges_L_S,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage RS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
