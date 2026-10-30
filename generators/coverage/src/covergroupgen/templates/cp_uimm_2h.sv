    cp_uimm_2h : coverpoint unsigned'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins uimm[] = {0, 2}; // halfword offsets for c.lh, c.lhu, and c.sh
    }
