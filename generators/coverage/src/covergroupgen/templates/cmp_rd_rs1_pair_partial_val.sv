    cmp_rd_rs1_pair_partial_val : coverpoint (
            (ins.current.rd_val[`XLEN-1:0] == ins.prev.rd_val[`XLEN-1:0]) ^
            (ins.current.rd_val[2*`XLEN-1:`XLEN] == ins.prev.rd_val[2*`XLEN-1:`XLEN])
        ) iff (ins.trap == 0)
        {
        // Cases where rd and rs1 have matching high or low halves but not both
            bins rd_pair_partial_equal_val_rs1 = {1};
            bins rd_pair_partial_not_equal_val_rs1 = {0};
        }
