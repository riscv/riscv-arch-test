    cp_rs2_pair : coverpoint ins.get_gpr_reg(ins.current.rs2)  iff (ins.trap == 0 )  {
        // RS2 register assignment, even registers only
        bins reg_pair[] = {[$:$]} with (item % 2 == 0);
    }
