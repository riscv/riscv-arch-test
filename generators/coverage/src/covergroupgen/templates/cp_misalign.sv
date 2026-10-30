    cp_misalign : coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] iff (ins.trap == 0) {
        // all 8 byte offsets within a doubleword
    }
