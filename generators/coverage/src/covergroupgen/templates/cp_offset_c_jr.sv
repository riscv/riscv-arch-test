    cp_offset : coverpoint {ins.current.rs1_val - ins.get_pc()}[`UDB_MXLEN-1]  iff (ins.trap == 0 )  {
        // c.jalr / c.jr destination in rs1 is forward/backward
    }
    cp_offset_lsbs : coverpoint ins.current.rs1_val[1:0]  iff (ins.trap == 0 )  {
        // c.jalr / c.jr destination is a multiple of 4 + 0/1/2/3
    }
