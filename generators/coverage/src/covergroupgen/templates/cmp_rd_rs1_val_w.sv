    cmp_rd_rs1_val_w : coverpoint (ins.current.rd_val[31:0] == ins.current.rd_val_pre[31:0]) iff (ins.trap == 0) {
        // Compare the lowest 32 bits of current rd value to the
        // lowest 32 bits of the value rd held before this instruction, which is the comparand
        bins rd_equal_val_w_rs1  = {1}; // Cases where the lowest 32 bits of rd and rs1 are equal
        bins rd_not_equal_val_w_rs1  = {0}; // Cases where the lowest 32 bits of rd and rs1 are not equal
    }
