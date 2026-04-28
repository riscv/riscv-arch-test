    cp_imm_mul_8sp : coverpoint ins.current.imm iff (ins.trap == 0) {
        // Immediate Multiples of 8
        bins offset[] = {[0:504]} with (item % 8 == 0);
    }
