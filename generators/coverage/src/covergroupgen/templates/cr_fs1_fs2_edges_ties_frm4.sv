    cp_fs1_ties_frm4 : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // FS1 exact-tie values (Single Precision)
        bins pos0p5   = {32'h3f000000};
        bins neg0p5   = {32'hbf000000};
        bins pos2p5   = {32'h40200000};
        bins neg2p5   = {32'hc0200000};
        bins postie   = {32'h4b800000};
        bins negtie   = {32'hcb800000};
    }

    cp_fs2_tie_partner_frm4 : coverpoint unsigned'(ins.current.fs2_val[31:0])  iff (ins.trap == 0 )  {
        // FS2 partner that makes the exact result a tie
        bins pos1     = {32'h3f800000};
        bins neg1     = {32'hbf800000};
    }

    cp_frm_ties_frm4 : coverpoint get_frm(ins.ops[4].val)  iff (ins.trap == 0 )  {
        // Only RNE and RMM are distinguished by an exact tie
        bins rne = {rne};
        bins rmm = {rmm};
    }

    cr_fs1_fs2_edges_ties_frm4 : cross cp_fs1_ties_frm4,cp_fs2_tie_partner_frm4,cp_frm_ties_frm4  iff (ins.trap == 0 )  {
        // Cross coverage FS1 exact ties, FS2 tie partner, rounding mode
    }
