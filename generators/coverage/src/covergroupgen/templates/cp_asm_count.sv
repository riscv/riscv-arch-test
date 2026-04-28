    cp_asm_count : coverpoint ins.ins_str == "INSTR"  iff (ins.trap == 0 )  {
        // Number of times instruction is executed
        bins count[]  = {1};
    }
