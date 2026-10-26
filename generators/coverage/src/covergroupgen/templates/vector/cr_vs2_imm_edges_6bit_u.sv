    //////////////////////////////////////////////////////////////////////////////////
    // cr_vs2_imm_edges_6bit_u
    //////////////////////////////////////////////////////////////////////////////////

    cp_imm_edges_6bit_u : coverpoint unsigned'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins b_0 = {0};
        bins b_1 = {1};
        bins b_2 = {2};
        bins b_3 = {3};
        bins b_4 = {4};
        bins b_7 = {7};
        bins b_8 = {8};
        bins b_9 = {9};
        bins b_15 = {15};
        bins b_16 = {16};
        bins b_17 = {17};
        bins b_30 = {30};
        bins b_31 = {31};
        bins b_32 = {32};
        bins b_33 = {33};
        bins b_62 = {62};
        bins b_63 = {63};
    }

    cr_vs2_imm_edges : cross cp_vs2_edges,cp_imm_edges_6bit_u  iff (ins.trap == 0 )  {
        // Cross coverage of VS2 edges and 5 bit imm edge values (unsigned)
    }

    //// end cr_vs2_imm_edges_6bit_u ////////////////////////////////////////////////
