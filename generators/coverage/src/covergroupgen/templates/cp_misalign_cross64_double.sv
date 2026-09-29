    cp_misalign_cross64_double : coverpoint 6'(ins.current.rs1_val + ins.current.imm) iff (ins.trap == 0) {
        // Does the 8-byte access cross a 64-byte boundary (and so a 16-, 32- or 64-byte cache line or bus beat)?
        bins no  = {[0:56]};
        bins yes = {[57:63]};
    }
