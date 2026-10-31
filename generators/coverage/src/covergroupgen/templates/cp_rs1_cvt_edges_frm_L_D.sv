    cp_rs1_cvt_edges_L_D : coverpoint unsigned'(ins.current.rs1_val[63:0])  iff (ins.trap == 0 )  {
        // RS1 integers whose conversion depends on the rounding mode
        bins tie_even_down            = {64'h0020000000000001};
        bins tie_even_up              = {64'h0020000000000003};
        bins neg_tie                  = {64'hffdfffffffffffff};
        bins below_tie                = {64'h0040000000000001};
        bins sticky                   = {64'h4000000000000201};
        bins carry_max                = {64'h7ffffffffffffe00};
        bins carry_umax               = {64'hfffffffffffffc00};
        bins min                      = {64'h8000000000000000};
        bins max                      = {64'h7fffffffffffffff};
    }

    cr_rs1_cvt_edges_frm_L_D : cross cp_rs1_cvt_edges_L_D,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage RS1 conversion edges, static rounding modes
        ignore_bins dyn = binsof(cp_frm_2) intersect {dyn};
    }
