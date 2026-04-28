    cp_imm_5bit : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins imm[] = {[-16:15]}; // 5 bit signed immediates for vector instructions
    }
