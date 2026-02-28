    cmp_rd_rs1_c : coverpoint ins.get_gpr_c_reg(ins.current.rd)  iff (ins.current.rd == ins.current.rs1 & ins.trap == 0 )  {
        // RD and RS1 register (assignment) WAR Hazard
    }
