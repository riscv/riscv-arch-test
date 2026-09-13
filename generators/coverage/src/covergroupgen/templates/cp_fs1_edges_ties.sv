    cp_fs1_edges_ties : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 exact-tie values (Single Precision): the only operands where RMM differs from RNE
        bins pos0p5   = {32'h3f000000};
        bins neg0p5   = {32'hbf000000};
        bins pos2p5   = {32'h40200000};
        bins neg2p5   = {32'hc0200000};
        bins postie   = {32'h4b800000};
        bins negtie   = {32'hcb800000};
    }

    cp_frm_ties : coverpoint get_frm(ins.ops[2].val)  iff (ins.trap == 0 )  {
        // Only RNE and RMM are distinguished by an exact tie
        bins rne = {rne};
        bins rmm = {rmm};
    }

    cr_fs1_edges_ties_frm : cross cp_fs1_edges_ties,cp_frm_ties  iff (ins.trap == 0 )  {
        // Cross coverage FS1 exact ties, rounding mode
    }
