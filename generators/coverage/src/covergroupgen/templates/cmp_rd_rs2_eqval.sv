    cmp_rd_rs2_eqval : coverpoint ins.current.rd_val == ins.current.rs2_val  iff (ins.trap == 0 )  {
        // Compare RD and RS2 register values
        bins rd_eqval_rs2  = {1};
        bins rd_neval_rs2  = {0};
    }
