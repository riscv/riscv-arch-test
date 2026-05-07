    cmp_rd_rs1_pair_partial_val : coverpoint (
            (ins.current.rd_val == ins.prev.rd_val) ^
            (ins.current.rd_next_val == ins.prev.rd_next_val)
        ) iff (ins.trap == 0)
        {
        // Cases where rd and rs1 have matching high or low halves but not both
            bins rd_pair_partial_equal_val_rs1 = {1};
            bins rd_pair_partial_not_equal_val_rs1 = {0};
        }
