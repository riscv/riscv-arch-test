    cmp_rd_rs1_val_w : coverpoint (ins.current.rd_val[31:0] == ins.prev.rd_val[31:0]) iff (ins.trap == 0) {
        // Compare the least significant 32 bits of rd and rs1 register values
        bins rd_equal_val_w_rs1  = {1}; // Cases where the least significant 32 bits of rd and rs1 are equal
        bins rd_not_equal_val_w_rs1  = {0}; // Cases where the least significant 32 bits of rd and rs1 are not equal
    }
