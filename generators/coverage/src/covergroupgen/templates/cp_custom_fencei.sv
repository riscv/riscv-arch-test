    // Custom coverpoints for fence.i

    // The test fetches the old instruction and records it, stores a new instruction
    // (sw, or sh of c.li when Zca is present), executes fence.i, and records the
    // instruction fetched after fence.i. This coverpoint only records that each
    // fence.i encoding ran.

    cp_custom_fencei : coverpoint ins.current.insn  {
        bins fencei            = {32'h0000100f}; // normal fence.i
        bins fencei_nonzerors1 = {32'h0001100f}; // fence.i with nonzero rs1 ignores this field
        bins fencei_nonzerord  = {32'h0000108f}; // fence.i with nonzero rd ignores this field
        bins fencei_nonzerof12 = {32'h0010100f}; // fence.i with nonzero funct12 ignores this field
    }
