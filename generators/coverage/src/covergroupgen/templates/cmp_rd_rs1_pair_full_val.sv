    cmp_rd_rs1_pair_full_val : coverpoint (ins.current.rd_val == ins.prev.rd_val) iff (ins.trap == 0) {
        // Compare RD current to RD previous value which is basically rs1 current value for the entire width of the register pair
        bins rd_pair_equal_val_rs1 = {1};
        bins rd_pair_not_equal_val_rs1 = {0};
    }
