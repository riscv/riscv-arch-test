    // checking 2,1,0,-1,-2 stride, since elements are 64 bits, each stride is 8 bytes
    cp_rs2_edges_ls_e64 : coverpoint signed'(ins.current.rs2_val) {
        bins n2     = {-16};
        bins n1     = {-8};
        bins zero   = {0};
        bins p1     = {8};
        bins p2     = {16};
    }
