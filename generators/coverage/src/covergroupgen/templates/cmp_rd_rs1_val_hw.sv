    cmp_rd_rs1_val_hw : coverpoint (ins.current.rd_val[15:0] == ins.current.rd_val_pre[15:0]) iff (ins.trap == 0) {
        // Compare the lowest 16 bits of current rd value to
        // lowest 16 bits of the value rd held before this instruction, which is the comparand
    }
