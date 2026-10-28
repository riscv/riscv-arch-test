    cp_offset : coverpoint ins.jump_backward(signed'(ins.current.rs1_val) + signed'(ins.current.imm))  iff (ins.trap == 0 )  {
        // jalr destination in rs1+imm is forward/backward
    }
    cp_offset_lsbs : coverpoint {ins.current.rs1_val[0], ins.current.imm[0]}  iff (ins.trap == 0 )  {
        // jalr destination is a multiple of 4 + 0/1.  Only check for the +0/1, with each lsb of rs1 and imm
    }
