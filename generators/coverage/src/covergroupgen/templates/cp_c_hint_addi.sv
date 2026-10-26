    // c.addi with rd != 0, imm = 0 is a hint
    cp_c_hint_addi : coverpoint ins.get_gpr_reg(ins.current.rd) iff (ins.trap == 0 && ins.current.imm == 0) {
        ignore_bins x0 = {x0}; // rd = x0 with imm = 0 is c.nop
    }
