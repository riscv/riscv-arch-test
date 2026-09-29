    cr_memval_rs2_minmax_word : coverpoint {ins.current.rd_val[31:0], ins.current.rs2_val[31:0]} iff (ins.trap == 0) {
        // Old memory word (returned in rd) and rs2 word at opposite signed extremes,
        // where signed and unsigned comparisons disagree
        bins mem_min_rs2_max = {64'h80000000_7fffffff};
        bins mem_max_rs2_min = {64'h7fffffff_80000000};
    }
