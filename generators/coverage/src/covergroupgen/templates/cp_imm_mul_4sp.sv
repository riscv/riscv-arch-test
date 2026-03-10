    cp_imm_mul_4sp : coverpoint ins.current.imm iff (ins.trap == 0) {
        // Immediate Multiples of 4
        bins offset[] = {[0:252]} with (item % 4 == 0);
    }
