    cp_fs1_ties_frm4_H : coverpoint unsigned'(ins.current.fs1_val[15:0])  iff (ins.trap == 0 )  {
        // FS1 exact-tie values (Half Precision)
        bins pos0p5   = {16'h3800};
        bins neg0p5   = {16'hb800};
        bins pos2p5   = {16'h4100};
        bins neg2p5   = {16'hc100};
        bins postie   = {16'h6800};
        bins negtie   = {16'he800};
    }

    cp_fs2_tie_partner_frm4_H : coverpoint unsigned'(ins.current.fs2_val[15:0])  iff (ins.trap == 0 )  {
        // FS2 partner that makes the exact result a tie
        bins pos1     = {16'h3c00};
        bins neg1     = {16'hbc00};
    }

    cp_frm_ties_frm4_H : coverpoint get_frm(ins.ops[4].val)  iff (ins.trap == 0 )  {
        // Only RNE and RMM are distinguished by an exact tie
        bins rne = {rne};
        bins rmm = {rmm};
    }

    cr_fs1_fs2_edges_ties_frm4_H : cross cp_fs1_ties_frm4_H,cp_fs2_tie_partner_frm4_H,cp_frm_ties_frm4_H  iff (ins.trap == 0 )  {
        // Cross coverage FS1 exact ties, FS2 tie partner, rounding mode
    }
