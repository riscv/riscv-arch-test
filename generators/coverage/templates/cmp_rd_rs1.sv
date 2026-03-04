    cmp_rd_rs1 : coverpoint ins.get_gpr_reg(ins.current.rd)  iff (ins.current.rd == ins.current.rs1 & ins.trap == 0 )  {
        // Compare assignments of all registers
    }
