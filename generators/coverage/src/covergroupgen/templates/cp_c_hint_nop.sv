    // c.nop with imm != 0 is a hint
    cp_c_hint_nop : coverpoint signed'(ins.current.imm) iff (ins.trap == 0) {
        bins imm[] = {[-32:31]};
        ignore_bins zero = {0};
    }
