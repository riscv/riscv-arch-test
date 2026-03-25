    cmp_rd_rs1_val_hw : coverpoint (ins.current.rd_val[15:0] == ins.prev.rd_val[15:0]) iff (ins.trap == 0) {
        // Compare the least significant 16 bits of rd and rs1 register values
        bins rd_eqval_hw_rs1  = {1}; // Cases where the least significant 16 bits of rd and rs1 are equal
        bins rd_neval_hw_rs1  = {0}; // Cases where the least significant 16 bits of rd and rs1 are not equal
    }
