    // C.MOP.n is defined to not write any register.  The test seeds registers, executes the
    // instruction, and writes them to the signature, so the coverpoint just checks execution.

    cp_custom_mop_no_write : coverpoint ins.ins_str == "INSTR"  iff (ins.trap == 0 )  {
        bins no_write  = {1};
    }
