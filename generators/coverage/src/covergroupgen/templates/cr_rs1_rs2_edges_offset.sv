    cr_rs1_rs2_edges_offset : cross cp_rs1_edges,cp_rs2_edges  {
        // Cross coverage of RS1 edges and RS2 edges, which exercises the comparison
    }
    // The comparison does not depend on the branch direction, so direction is crossed only with the outcome:
    // forward and backward branches, each taken and not taken.
    cp_branch_taken : coverpoint {ins.current.insn[14:12],                                        // funct3
                                  ins.current.rs1_val == ins.current.rs2_val,                     // rs1 = rs2
                                  $signed(ins.current.rs1_val) < $signed(ins.current.rs2_val),    // rs1 < rs2 (signed)
                                  $unsigned(ins.current.rs1_val) < $unsigned(ins.current.rs2_val) // rs1 < rs2 (unsigned)
                                 } iff (ins.trap == 0 )  {
        wildcard bins taken     = {6'b000_1_?_?, 6'b001_0_?_?, 6'b100_?_1_?, 6'b101_?_0_?, 6'b110_?_?_1, 6'b111_?_?_0};
        wildcard bins not_taken = {6'b000_0_?_?, 6'b001_1_?_?, 6'b100_?_0_?, 6'b101_?_1_?, 6'b110_?_?_0, 6'b111_?_?_1};
    }
    cr_offset_branch_taken : cross cp_offset,cp_branch_taken;
