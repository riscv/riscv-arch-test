    cp_imm_mul_8 : coverpoint ins.current.imm iff (ins.trap == 0) {
        // Immediate Multiples of 8
        bins offset[] = {[0:248]} with (item % 8 == 0);
    }
