    cp_rs2_nx0 : coverpoint ins.get_gpr_reg(ins.current.rs2)  iff (ins.trap == 0 )  {
        // RS2 register assignment (excluding x0)
        ignore_bins x0 = {x0};
    }
