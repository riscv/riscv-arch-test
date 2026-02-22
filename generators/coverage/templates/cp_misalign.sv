
    `ifdef XLEN32
        cp_misalign : coverpoint {ins.current.rs1_val + ins.current.imm}[1:0] iff (ins.trap == 0) {
            // test all 4 possible offsets of word alignments
        }
    `else
        cp_misalign : coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] iff (ins.trap == 0) {
            // test all 8 possible offsets of doubleword alignments
        }
    `endif
