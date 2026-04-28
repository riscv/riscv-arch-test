    cp_uimm_5 : coverpoint unsigned'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins uimm[] = {[0:31]}; // 5 bit immediates for csr*i, iw, and vector instructions
    }
