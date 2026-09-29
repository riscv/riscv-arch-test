    cr_memval_rs2_minmax_double : coverpoint {ins.current.rd_val[63:0], ins.current.rs2_val[63:0]} iff (ins.trap == 0) {
        // Old memory doubleword (returned in rd) and rs2 at opposite signed extremes,
        // where signed and unsigned comparisons disagree
        bins mem_min_rs2_max = {128'h8000000000000000_7fffffffffffffff};
        bins mem_max_rs2_min = {128'h7fffffffffffffff_8000000000000000};
    }
