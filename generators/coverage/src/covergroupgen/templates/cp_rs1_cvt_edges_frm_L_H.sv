    cp_rs1_cvt_edges_L_H : coverpoint unsigned'(ins.current.rs1_val[63:0])  iff (ins.trap == 0 )  {
        // RS1 integers whose conversion depends on the rounding mode
        bins tie_even_down            = {64'h0000000000000801};
        bins tie_even_up              = {64'h0000000000000803};
        bins neg_tie                  = {64'hfffffffffffff7ff};
        bins below_tie                = {64'h0000000000001001};
        bins sticky                   = {64'h0000000000004009};
        bins below_overflow           = {64'h000000000000ffef};
        bins overflow_tie             = {64'h000000000000fff0};
        bins neg_overflow_tie         = {64'hffffffffffff0010};
        bins min                      = {64'h8000000000000000};
    }

    cr_rs1_cvt_edges_frm_L_H : cross cp_rs1_cvt_edges_L_H,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage RS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
