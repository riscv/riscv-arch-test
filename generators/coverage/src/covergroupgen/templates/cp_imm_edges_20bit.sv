    cp_imm_edges_20bit : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        // Imm Edges
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
        bins p10   = {1024};
        bins p11   = {2048};
        bins p12   = {4096};
        bins p13   = {8192};
        bins p14   = {16384};
        bins p15   = {32768};
        bins p16   = {65536};
        bins p17   = {131072};
        bins p18   = {262144};
        bins halfm2 = {524286};
        bins halfm1 = {524287};
        bins n1     = {-1};
        bins n2     = {-2};
        bins minp1_2  = {-524287};
        bins min_2    = {-524288};
    }
