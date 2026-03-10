//////////////////////////////////////////////////////////////////////////////////
    // cr_vs2_imm_edges
    //////////////////////////////////////////////////////////////////////////////////

    cp_imm_edges_5bit : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins b_0 = {0};
        bins b_1 = {1};
        bins b_2 = {2};
        bins b_14 = {14};
        bins b_15 = {15};
        bins b_n16 = {-16};
        bins b_n15 = {-15};
        bins b_n2 = {-2};
        bins b_n1 = {-1};
    }

    cr_vs2_imm_edges : cross cp_vs2_edges,cp_imm_edges_5bit  iff (ins.trap == 0 )  {
        // Cross coverage of VS2 edges and 5 bit imm edge values
    }

    //// end cr_vs2_imm_edges////////////////////////////////////////////////
