    cp_imm_edges_c : coverpoint unsigned'(ins.current.imm[5:0])  iff (ins.trap == 0 )  {
        bins b_1 = {1};
        bins b_2 = {2};
        bins b_3 = {3};
        bins b_4 = {4};
        bins b_8 = {8};
        bins b_14 = {14};
        bins b_15 = {15};
        bins b_16 = {16};
        bins b_17 = {17};
        bins b_30 = {30};
        bins b_31 = {31};
        `ifdef XLEN64
            bins b_32 = {32};
            bins b_33 = {33};
            bins b_48 = {48};
            bins b_62 = {62};
            bins b_63 = {63};
        `endif
    }
    cr_rs1_imm_edges_c : cross cp_rs1_edges,cp_imm_edges_c  iff (ins.trap == 0 )  {
        // Cross coverage of RS1 and Imm edges
    }
