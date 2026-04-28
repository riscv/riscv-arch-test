    // Custom coverpoints for fence.i

    // the test should do some self-modifying code and then a fence.i and then run the code
    // this is too complicated to express with a coverpoint, so just check that the fence.i
    // is executed, and leave it to the test code to do the right thing

    cp_custom_fencei : coverpoint ins.current.insn  {
        bins fencei            = {32'h0000100f}; // normal fence.i
        bins fencei_nonzerors1 = {32'h0001100f}; // fence.i with nonzero rs1 ignores this field
        bins fencei_nonzerord  = {32'h0000108f}; // fence.i with nonzero rd ignores this field
        bins fencei_nonzerof12 = {32'h0010100f}; // fence.i with nonzero funct12 ignores this field
    }
