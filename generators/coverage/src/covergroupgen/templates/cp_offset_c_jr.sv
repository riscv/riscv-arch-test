    cp_offset : coverpoint signed'(ins.current.rs1_val) - ins.get_pc() iff (ins.trap == 0 )  {
        // c.jalr / c.jr destination in rs1
        bins neg  = {[$:-1]};
        bins pos  = {[1:$]};
    }
    cp_offset_lsbs : coverpoint ins.current.rs1_val[1:0]  iff (ins.trap == 0 )  {
        // c.jalr / c.jr destination is a multiple of 4 + 0/1/2/3
    }
