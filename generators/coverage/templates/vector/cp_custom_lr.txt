    cp_custom_aqrl : coverpoint ins.current.insn[26:25]  iff (ins.trap == 0 )  {
        // Combinations of acquire and release
        ignore_bins rl_noaq = {2'b01};
    }
    cp_custom_rd_edges : coverpoint ins.current.rd_val iff (ins.trap == 0) {
        `ifdef XLEN32
            bins zero = {0};
            bins one  = {32'b00000000000000000000000000000001};
            bins max  = {32'b11111111111111111111111111111111};
        `else // XLEN64
            bins zero = {0};
            bins one  = {64'b0000000000000000000000000000000000000000000000000000000000000001};
            bins max  = {64'b1111111111111111111111111111111111111111111111111111111111111111};
        `endif
    }
