    cmp_rd_rs1_val_lsb : coverpoint (ins.current.rd_val[7:0] == ins.prev.rd_val[7:0]) iff (ins.trap == 0) {
        // Compare the least significant byte of current rd value to the
        // least significant byte of previous rd value (which is the same as rs1 value for the current instruction)
    }
