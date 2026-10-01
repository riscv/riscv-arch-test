    cp_uimm_2 : coverpoint unsigned'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins uimm[] = {[0:3]}; // 2-bit byte offsets for c.lbu and c.sb
    }
