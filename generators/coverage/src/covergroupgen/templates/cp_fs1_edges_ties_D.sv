    cp_fs1_edges_ties_D : coverpoint unsigned'(ins.current.fs1_val[63:0])  iff (ins.trap == 0 )  {
        // FS1 exact-tie values (Double Precision): the only operands where RMM differs from RNE
        bins pos0p5   = {64'h3fe0000000000000};
        bins neg0p5   = {64'hbfe0000000000000};
        bins pos2p5   = {64'h4004000000000000};
        bins neg2p5   = {64'hc004000000000000};
        bins postie   = {64'h4340000000000000};
        bins negtie   = {64'hc340000000000000};
    }

    cp_frm_ties_D : coverpoint get_frm(ins.ops[2].val)  iff (ins.trap == 0 )  {
        // Only RNE and RMM are distinguished by an exact tie
        bins rne = {rne};
        bins rmm = {rmm};
    }

    cr_fs1_edges_ties_frm_D : cross cp_fs1_edges_ties_D,cp_frm_ties_D  iff (ins.trap == 0 )  {
        // Cross coverage FS1 exact ties, rounding mode
    }
