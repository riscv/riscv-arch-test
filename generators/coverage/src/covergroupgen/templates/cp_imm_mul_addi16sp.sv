    cp_imm_mul_addi16sp : coverpoint signed'(ins.current.imm) iff (ins.trap == 0) {
        // Immediate Multiples of 16
        bins offset[] = {[-512:496]} with (item % 16 == 0);
        ignore_bins zero = {0};
    }
