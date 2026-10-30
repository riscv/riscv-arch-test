    cp_misalign_cross64_hword : coverpoint {ins.current.rs1_val + ins.current.imm}[5:0] iff (ins.trap == 0) {
        // Does the 2-byte access cross a 64-byte boundary (and so a 16-, 32- or 64-byte cache line or bus beat)?
        bins no  = {[0:62]};
        bins yes = {[63:63]};
    }
