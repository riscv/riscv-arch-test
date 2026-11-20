    cp_offset : coverpoint ins.current.imm[`UDB_MXLEN-1]  iff (ins.trap == 0 & ins.current.imm != 0)  {
        // Branch Immediate Offset value is forward/backward
    }
