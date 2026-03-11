    // checking 2,1,0,-1,-2 stride, since elements are 16 bits, each stride is 2 bytes
    cp_rs2_edges_ls_e16 : coverpoint signed'(ins.current.rs2_val) {
        bins n2     = {-4};
        bins n1     = {-2};
        bins zero   = {0};
        bins p1     = {2};
        bins p2     = {4};
    }
