    cmp_rd_rs2_c : coverpoint ins.get_gpr_c_reg(ins.current.rd)  iff (ins.current.rd == ins.current.rs2 & ins.trap == 0 )  {
        // RD and RS2 register (assignment) WAR Hazard
    }
