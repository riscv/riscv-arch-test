    // checking 2,1,0,-1,-2 stride, since elements are 8 bits, each stride is 1 byte
    cp_rs2_edges_ls_e8 : coverpoint signed'(ins.current.rs2_val) {
        bins n2     = {-2};
        bins n1     = {-1};
        bins zero   = {0};
        bins p1     = {1};
        bins p2     = {2};
    }
