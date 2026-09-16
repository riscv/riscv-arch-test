    cp_fs1_edges_ties_H : coverpoint unsigned'(ins.current.fs1_val[15:0])  iff (ins.trap == 0 )  {
        // FS1 exact-tie values (Half Precision): the only operands where RMM differs from RNE
        bins pos0p5   = {16'h3800};
        bins neg0p5   = {16'hb800};
        bins pos2p5   = {16'h4100};
        bins neg2p5   = {16'hc100};
        bins postie   = {16'h6800};
        bins negtie   = {16'he800};
    }

    cp_frm_ties_H : coverpoint get_frm(ins.ops[2].val)  iff (ins.trap == 0 )  {
        // Only RNE and RMM are distinguished by an exact tie
        bins rne = {rne};
        bins rmm = {rmm};
    }

    cr_fs1_edges_ties_frm_H : cross cp_fs1_edges_ties_H,cp_frm_ties_H  iff (ins.trap == 0 )  {
        // Cross coverage FS1 exact ties, rounding mode
    }
