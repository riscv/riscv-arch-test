    cp_zcmp_mvsa01 : coverpoint ins.current.insn[9:7] iff (ins.trap == 0) {
        bins s0 = {3'd0};
        bins s1 = {3'd1};
        bins s2 = {3'd2};
        bins s3 = {3'd3};
        bins s4 = {3'd4};
        bins s5 = {3'd5};
        bins s6 = {3'd6};
        bins s7 = {3'd7};
    }
