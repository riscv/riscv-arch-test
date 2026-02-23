    cmp_rs1_rs2_eqval : coverpoint ins.current.rs1_val == ins.current.rs2_val  iff (ins.trap == 0 )  {
        // Compare RS1 and RS2 register values
        bins rs1_eqval_rs2  = {1};
        bins rs1_neval_rs2  = {0};
    }
