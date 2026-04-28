    cp_imm_edges_uimm : coverpoint unsigned'(ins.current.imm[5:0])  iff (ins.trap == 0 )  {
        bins b_0 = {0};
        bins b_1 = {1};
        bins b_19 = {19};
        bins b_30 = {30};
        bins b_31 = {31};
        `ifdef XLEN64
            bins b_32 = {32};
            bins b_33 = {33};
            bins b_45 = {45};
            bins b_62 = {62};
            bins b_63 = {63};
        `endif
    }
    cr_rs1_imm_edges_uimm : cross cp_rs1_edges,cp_imm_edges_uimm  iff (ins.trap == 0 )  {
        // Cross coverage of RS1 and Imm edges
    }
