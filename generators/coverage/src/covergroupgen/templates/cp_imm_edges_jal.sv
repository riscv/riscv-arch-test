    cp_imm_edges_jal : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        // imm is the jump offset
        bins b_4     = {4};
        bins b_8     = {8};
        bins b_16    = {16};
        bins b_32    = {32};
        bins b_64    = {64};
        bins b_128   = {128};
        bins b_256   = {256};
        bins b_512   = {512};
        bins b_1024  = {1024};
        bins b_2048  = {2048};
        bins b_4096  = {4096};
        bins b_8192  = {8192};
        bins b_m4    = {-4};
        bins b_m8    = {-8};
        bins b_m16   = {-16};
        bins b_m32   = {-32};
        bins b_m64   = {-64};
        bins b_m128  = {-128};
        bins b_m256  = {-256};
        bins b_m512  = {-512};
        bins b_m1024 = {-1024};
        bins b_m2048 = {-2048};
        bins b_m4096 = {-4096};
        bins b_m8192 = {-8192};
    }
