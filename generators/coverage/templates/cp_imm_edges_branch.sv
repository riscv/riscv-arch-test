    cp_imm_edges_branch : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        // some corner values of branch offsets
        bins b_4 = {4};
        bins b_8 = {8};
        bins b_16 = {16};
        bins b_2048 = {2048};
        // bins b_4092 = {4092}; // removed for now because gcc is not generating a branch by this much correctly
        bins b_m4 = {-4};
        bins b_m8 = {-8};
        bins b_m4096 = {-4096};
    }
