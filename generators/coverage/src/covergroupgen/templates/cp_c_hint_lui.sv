    // c.lui with rd = 0, imm != 0 is a hint
    cp_c_hint_lui : coverpoint signed'(ins.current.imm) iff (ins.trap == 0 && ins.get_gpr_reg(ins.current.rd) == x0) {
        bins imm[] = {[-32:31]};
        ignore_bins zero = {0};
    }
