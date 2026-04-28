    cp_memval_byte : coverpoint {ins.current.rd_val[7:0]} iff (ins.trap == 0) {
        bins zero = {8'h00};
        bins one  = {8'h01};
        bins max  = {8'h7f};
        bins min  = {8'h80};
        bins mone = {8'hff};
    }
