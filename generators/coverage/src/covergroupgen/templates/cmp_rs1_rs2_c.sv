    cmp_rs1_rs2_c : coverpoint ins.get_gpr_c_reg(ins.current.rs1)  iff (ins.current.rs1 == ins.current.rs2 & ins.trap == 0 )  {
        // RD and RS2 register (assignment) WAR Hazard
    }
