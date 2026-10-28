    cp_offset : coverpoint {ins.current.rs1_val + ins.current.imm - ins.get_pc()}[`UDB_MXLEN-1]  iff (ins.trap == 0 )  {
        // jalr destination in rs1+imm is forward/backward
    }
    cp_offset_lsbs : coverpoint {ins.current.rs1_val[0], ins.current.imm[0]}  iff (ins.trap == 0 )  {
        // jalr destination is a multiple of 4 + 0/1.  Only check for the +0/1, with each lsb of rs1 and imm
    }
