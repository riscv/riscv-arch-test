cmp_rd_rs1_val_eq : coverpoint (ins.current.rd_val == ins.prev.rd_val) iff (ins.trap == 0) {
    // Compare RD current to RD previous value which is basically rs1 current value
    bins rd_val_eq_rs1  = {1}; // This bin is hit when rd_val is equal to rs1 value (which is the previous rd_val)
    bins rd_val_neq_rs1 = {0}; // This bin is hit when rd_val is not equal to rs1 value (which is the previous rd_val)
}
