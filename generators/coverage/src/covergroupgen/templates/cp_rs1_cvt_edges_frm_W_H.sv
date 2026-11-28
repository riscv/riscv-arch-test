    cp_rs1_cvt_edges_W_H : coverpoint unsigned'(ins.current.rs1_val[31:0])  iff (ins.trap == 0 )  {
        // RS1 integers whose conversion depends on the rounding mode
        bins tie_even_down            = {32'h00000801};
        bins tie_even_up              = {32'h00000803};
        bins neg_tie                  = {32'hfffff7ff};
        bins below_tie                = {32'h00001001};
        bins sticky                   = {32'h00004009};
        bins below_overflow           = {32'h0000ffef};
        bins overflow_tie             = {32'h0000fff0};
        bins neg_overflow_tie         = {32'hffff0010};
        bins min                      = {32'h80000000};
    }

    cr_rs1_cvt_edges_frm_W_H : cross cp_rs1_cvt_edges_W_H,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage RS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
