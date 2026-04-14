    cmp_rd_rs1_val_d : coverpoint (ins.current.rd_val[63:0] == ins.prev.rd_val[63:0]) iff (ins.trap == 0) {
        // Compare the lowest 64 bits of current rd value to the
        // lowest 64 bits of previous rd value (which is the same as rs1 value for the current instruction)
        bins rd_equal_val_d_rs1  = {1}; // Cases where the lowest 64 bits of rd and rs1 are equal
        bins rd_not_equal_val_d_rs1  = {0}; // Cases where the lowest 64 bits of rd and rs1 are not equal
    }
