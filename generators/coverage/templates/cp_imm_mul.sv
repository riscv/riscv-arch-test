    cp_imm_mul : coverpoint ins.current.imm iff (ins.trap == 0) {
        // Immediate Multiples of 4
        bins offset[] = {[0:124]} with (item % 4 == 0);
    }
