    cp_offset : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        // Branch Immediate Offset value
        bins neg  = {[$:-1]};
        bins pos  = {[1:$]};
    }
