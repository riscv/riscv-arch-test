    cp_imm_5bit_u : coverpoint unsigned'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins uimm[] = {[0:31]}; // 5 bit unsigned immediates for vector instructions
    }
