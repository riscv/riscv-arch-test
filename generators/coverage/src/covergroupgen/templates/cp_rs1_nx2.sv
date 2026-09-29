    cp_rs1_nx2 : coverpoint ins.get_gpr_reg(ins.current.rs1) iff (ins.trap == 0) {
        // RS1 register assignment (excluding x0 and x2)
        ignore_bins x0 = {x0}; // rd = x0 is a HINT
        ignore_bins x2 = {x2}; // rd = x2 is c.addi16sp
    }
