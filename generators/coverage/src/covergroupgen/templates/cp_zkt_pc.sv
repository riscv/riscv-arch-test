    // Instruction without data operands that directly follows csrr cycle (or mcycle)
    cp_zkt_pc : coverpoint (ins.prev.inst_name == "csrrs" & (ins.prev.insn[31:20] == CSR_CYCLE | ins.prev.insn[31:20] == CSR_MCYCLE))  iff (ins.trap == 0)  {
        bins timed = {1};
    }
