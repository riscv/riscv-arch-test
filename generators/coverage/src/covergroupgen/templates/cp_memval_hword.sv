    cp_memval_hword : coverpoint {ins.current.rd_val[15:0]} iff (ins.trap == 0) {
        bins zero = {16'h0000};
        bins one  = {16'h0001};
        bins max  = {16'h7fff};
        bins min  = {16'h8000};
        bins mone = {16'hffff};
    }
