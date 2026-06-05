    // c.addi with rd != 0, imm = 0 is a hint
    cp_c_hint_addi : coverpoint ins.get_gpr_reg(ins.current.rd) iff (ins.trap == 0 && ins.current.imm == 0) {
        bins rd[] = {[x1:x31]}; // rd != x0
    }
