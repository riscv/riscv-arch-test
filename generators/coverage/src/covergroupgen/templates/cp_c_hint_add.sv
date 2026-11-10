    // c.add with rd = 0, rs2 != 0 is a hint
    cp_c_hint_add : coverpoint ins.get_gpr_reg(ins.current.rs2) iff (ins.trap == 0 && ins.get_gpr_reg(ins.current.rd) == x0) {
        ignore_bins x0 = {x0}; // rd = rs2 = x0 encodes c.ebreak
    }
