    cp_memval_double : coverpoint {ins.current.rd_val[63:0]} iff (ins.trap == 0) {
        bins zero = {64'h0000000000000000};
        bins one  = {64'h0000000000000001};
        bins max  = {64'h7fffffffffffffff};
        bins min  = {64'h8000000000000000};
        bins mone = {64'hffffffffffffffff};
    }
