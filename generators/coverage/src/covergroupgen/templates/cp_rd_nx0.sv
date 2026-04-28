    cp_rd_nx0 : coverpoint ins.get_gpr_reg(ins.current.rd) iff (ins.trap == 0) {
        // RD register assignment (excluding x0)
        ignore_bins x0 = {x0};
    }
