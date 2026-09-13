    cmp_rd_rs1_val_lsb : coverpoint (ins.current.rd_val[7:0] == ins.current.rd_val_pre[7:0]) iff (ins.trap == 0) {
        // Compare the least significant byte of current rd value to the
        // least significant byte of the value rd held before this instruction, which is the comparand
    }
