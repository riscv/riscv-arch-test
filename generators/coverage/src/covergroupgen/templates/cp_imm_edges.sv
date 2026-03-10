    cp_imm_edges : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins zero  = {0};
        bins p0    = {1};
        bins p1    = {2};
        bins three = {3};
        bins p2    = {4};
        bins p3    = {8};
        bins p4    = {16};
        bins p5    = {32};
        bins p6    = {64};
        bins p7    = {128};
        bins p8    = {256};
        bins p9    = {512};
        bins hm1   = {1023};
        bins p10   = {1024};
        bins max   = {2047};
        bins min   = {-2048};
        bins minp1 = {-2047};
        bins onesm1 = {-2};
        bins ones   = {-1};
        bins randomp = {1795};
    }
