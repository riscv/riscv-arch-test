    cp_imm_mul_addi4spn : coverpoint ins.current.imm iff (ins.trap == 0) {
        // Immediate Multiples of 4
        bins offset[] = {[4:1020]} with (item % 4 == 0);
    }
