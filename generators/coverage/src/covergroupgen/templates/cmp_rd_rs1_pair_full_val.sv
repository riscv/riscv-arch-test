    cmp_rd_rs1_pair_full_val : coverpoint (ins.current.rd_val == ins.prev.rd_val) iff (ins.trap == 0) {
        bins rd_pair_eqval_rs1 = {1};
        bins rd_pair_neqval_rs1 = {0};
    }
