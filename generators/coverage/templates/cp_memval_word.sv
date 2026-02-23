    cp_memval_word : coverpoint {ins.current.rd_val[31:0]} iff (ins.trap == 0) {
        bins zero = {32'h00000000};
        bins one  = {32'h00000001};
        bins max  = {32'h7fffffff};
        bins min  = {32'h80000000};
        bins mone = {32'hffffffff};
    }
