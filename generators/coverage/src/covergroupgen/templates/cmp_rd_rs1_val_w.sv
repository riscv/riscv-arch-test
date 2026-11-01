    cmp_rd_rs1_val_w : coverpoint (ins.current.rd_val[31:0] == ins.current.rd_val_pre[31:0]) iff (ins.trap == 0) {
        // Compare the lowest 32 bits of current rd value to the
        // lowest 32 bits of the value rd held before this instruction, which is the comparand
    }
