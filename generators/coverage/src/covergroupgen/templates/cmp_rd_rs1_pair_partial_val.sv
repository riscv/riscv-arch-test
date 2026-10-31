    cmp_rd_rs1_pair_partial_val : coverpoint (
            (ins.current.rd_val == ins.current.rd_val_pre) ^
            (ins.current.rd_upper_pair_val == ins.current.rd_upper_pair_val_pre)
        ) iff (ins.trap == 0)
        {
        // Cases where rd and rs1 have matching high or low halves but not both
        }
