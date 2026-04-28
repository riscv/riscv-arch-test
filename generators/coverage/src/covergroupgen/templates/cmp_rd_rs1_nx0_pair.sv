    cmp_rd_rs1_nx0_pair : coverpoint ins.get_gpr_reg(ins.current.rd)  iff (ins.current.rd == ins.current.rs1 & ins.trap == 0 )  {
        // Compare assignments of all even registers excluding x0
        ignore_bins x0 = {x0};
        bins reg_pair[] = {[$:$]} with (item % 2 == 0);
    }
