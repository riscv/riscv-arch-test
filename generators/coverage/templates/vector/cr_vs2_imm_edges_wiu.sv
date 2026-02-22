//////////////////////////////////////////////////////////////////////////////////
    // cr_vs2_imm_edges_wiu
    //////////////////////////////////////////////////////////////////////////////////

    cp_imm_edges_5bit_u : coverpoint unsigned'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins b_0 = {0};
        bins b_1 = {1};
        bins b_2 = {2};
        bins b_15 = {15};
        bins b_16 = {16};
        bins b_30 = {30};
        bins b_31 = {31};
    }

    cr_vs2_imm_edges_wiu : cross cp_vs2_edges_emul2,cp_imm_edges_5bit_u  iff (ins.trap == 0 )  {
        // Cross coverage of VS2 edges (emul = 2) and 5 bit imm edge values (unsigned)
    }

    //// end cr_vs2_imm_edges_wiu////////////////////////////////////////////////
