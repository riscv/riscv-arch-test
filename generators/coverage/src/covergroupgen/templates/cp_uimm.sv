    cp_uimm : coverpoint unsigned'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins uimm[] = {[0:`XLEN - 1]}; // 5/6 bit immediates
    }
