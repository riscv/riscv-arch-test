    cp_rs1_imm_rel : coverpoint ((ins.current.rs1_val == ins.current.imm2) ? 0 :
                                 (ins.current.rs1_val == ins.current.imm2 + 1) ? 1 :
                                 (ins.current.rs1_val == ins.current.imm2 - 1) ? 2 :
                                 (ins.current.rs1_val[31:0] == ins.current.imm2[31:0]) ? 3 : 4)  iff (ins.trap == 0 )  {
        // Relation of the rs1 value to the comparison constant
        bins equal = {0};
        bins plus1 = {1};
        bins minus1 = {2};
        `ifndef UDB_MXLEN_32
            bins low_word_equal_upper_differs = {3};
        `endif
    }
    cr_imm_edges_5bit_u_n0_rs1_rel : cross cp_imm_edges_5bit_u_n0,cp_rs1_imm_rel  iff (ins.trap == 0 )  {
        // Cross coverage of immediate edges and the relation of rs1 to the immediate
    }
