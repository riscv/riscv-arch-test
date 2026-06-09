    cp_asm_count : coverpoint ins.ins_str == "INSTR" iff (ins.trap == 0 && ins.current.imm == 0) {
        // Number of times the canonical INSTR (imm == 0) is executed
        bins count[] = {1};
    }
