    cp_imm_edges_6bit_n0 : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins b_1 = {1};
        bins b_2 = {2};
        bins b_3 = {3};
        bins b_4 = {4};
        bins b_8 = {8};
        bins b_16 = {16};
        bins b_30 = {30};
        bins b_31 = {31};
        bins b_32 = {-32};
        bins b_33 = {-31};
        bins b_62 = {-2};
        bins b_63 = {-1};
    }
