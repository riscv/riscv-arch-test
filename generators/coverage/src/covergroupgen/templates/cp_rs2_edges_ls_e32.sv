    // checking 2,1,0,-1,-2 stride, since elements are 32 bits, each stride is 4 bytes
    cp_rs2_edges_ls_e32 : coverpoint signed'(ins.current.rs2_val) {
        bins n2     = {-8};
        bins n1     = {-4};
        bins zero   = {0};
        bins p1     = {4};
        bins p2     = {8};
    }
