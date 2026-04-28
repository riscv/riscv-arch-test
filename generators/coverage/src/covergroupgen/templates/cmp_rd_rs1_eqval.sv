    cmp_rd_rs1_eqval : coverpoint ins.current.rd_val == ins.current.rs1_val  iff (ins.trap == 0 )  {
        // Compare RD and RS1 register values
        bins rd_eqval_rs1  = {1};
        bins rd_neval_rs1  = {0};
    }
