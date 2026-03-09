    cp_imm_edges_uimmw : coverpoint unsigned'(ins.current.imm[5:0])  iff (ins.trap == 0 )  {
        bins b_0 = {0};
        bins b_1 = {1};
        bins b_19 = {19};
        bins b_30 = {30};
        bins b_31 = {31};
    }
    cr_rs1_imm_edges_uimmw : cross cp_rs1_edges,cp_imm_edges_uimmw  iff (ins.trap == 0 )  {
        // Cross coverage of RS1 and Imm edges
    }
