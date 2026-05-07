cmp_rd_rs1_val_eq : coverpoint (ins.current.rd_val == ins.prev.rd_val) iff (ins.trap == 0) {
    // Compare rd current to rd previous value (which is the same as rs1 value for the current instruction)
}
