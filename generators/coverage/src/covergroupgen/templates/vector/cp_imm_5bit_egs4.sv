    cp_imm_5bit_egs4 : coverpoint unsigned'(ins.current.imm)  iff (ins.trap == 0 )  {
        bins uimm[] = {[0:31]}; // 5 bit unsigned immediates for EGS=4 vector crypto instructions (e.g. rnum for AES key schedule)
    }
