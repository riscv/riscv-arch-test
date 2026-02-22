    cp_vm : coverpoint ins.current.insn[25]  iff (ins.trap == 0 )  {
        // vm bit value for set/not set
        bins zero = {0};
        bins one  = {1}; // unmasked
    }
