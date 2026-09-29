    cp_misalign_cross64 : coverpoint (7'({ins.current.rs1_val + ins.current.imm}[5:0]) +
            (("@INSTR@" inside {"lh", "lhu", "sh"}) ? 7'd2 :
             ("@INSTR@" inside {"ld", "sd", "fld", "fsd", "c.ld", "c.sd", "c.ldsp", "c.sdsp"}) ? 7'd8 : 7'd4)) > 7'd64
            iff (ins.trap == 0) {
        // Does the access cross a 64-byte boundary (and so a 16-, 32- or 64-byte cache line or bus beat)?
        // The access size in bytes comes from the mnemonic: 2 for halfwords, 8 for doublewords, else 4.
        bins no  = {0};
        bins yes = {1};
    }
