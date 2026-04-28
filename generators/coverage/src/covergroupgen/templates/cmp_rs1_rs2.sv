    cmp_rs1_rs2 : coverpoint ins.get_gpr_reg(ins.current.rs1)  iff (ins.current.rs1 == ins.current.rs2 & ins.trap == 0 )  {
        // Compare assignments of all registers
    }
