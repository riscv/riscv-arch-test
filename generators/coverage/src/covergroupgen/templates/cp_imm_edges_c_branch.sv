    cp_imm_edges_c_branch : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        // +2 to +128 set each of offset[7:1] alone; -2^k sets offset[8:k] (offset range -256 to +254)
        bins b_2    = {2};
        bins b_4    = {4};
        bins b_8    = {8};
        bins b_16   = {16};
        bins b_32   = {32};
        bins b_64   = {64};
        bins b_128  = {128};
        bins b_m2   = {-2};
        bins b_m4   = {-4};
        bins b_m8   = {-8};
        bins b_m16  = {-16};
        bins b_m32  = {-32};
        bins b_m64  = {-64};
        bins b_m128 = {-128};
        bins b_m256 = {-256};
    }
