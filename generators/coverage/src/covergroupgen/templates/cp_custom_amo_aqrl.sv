    cp_custom_aqrl : coverpoint ins.current.insn[26:25]  iff (ins.trap == 0 )  {
    // All four combinations of acquire and release are legal on an AMO
    }
