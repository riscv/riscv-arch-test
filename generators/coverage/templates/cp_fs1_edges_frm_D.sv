    cp_fs1_edges_D : coverpoint unsigned'(ins.current.fs1_val[63:0])  iff (ins.trap == 0 )  {
        // FS1 edges (Double Precision)
        bins pos0             = {64'h0000000000000000};
        bins neg0             = {64'h8000000000000000};
        bins pos1             = {64'h3FF0000000000000};
        bins neg1             = {64'hBFF0000000000000};
        bins pos1p5           = {64'h3FF8000000000000};
        bins neg1p5           = {64'hBFF8000000000000};
        bins pos2             = {64'h4000000000000000};
        bins neg2             = {64'hc000000000000000};
        bins posminnorm       = {64'h0010000000000000};
        bins negminnorm       = {64'h8010000000000000};
        bins posmaxnorm       = {64'h7FEFFFFFFFFFFFFF};
        bins negmaxnorm       = {64'hFFEFFFFFFFFFFFFF};
        bins posmax_subnorm   = {64'h000FFFFFFFFFFFFF};
        bins negmax_subnorm   = {64'h800FFFFFFFFFFFFF};
        bins posmid_subnorm   = {64'h0008000000000000};
        bins negmid_subnorm   = {64'h8008000000000000};
        bins posmin_subnorm   = {64'h0000000000000001};
        bins negmin_subnorm   = {64'h8000000000000001};
        bins posinfinity      = {64'h7FF0000000000000};
        bins neginfinity      = {64'hFFF0000000000000};
        bins posQNaN          = {[64'h7FF8000000000000:64'h7FFFFFFFFFFFFFFF]};
        bins posSNaN          = {[64'h7FF0000000000001:64'h7FF7FFFFFFFFFFFF]};
        bins negQNaN          = {[64'hFFF8000000000000:64'hFFFFFFFFFFFFFFFF]};
        bins negSNaN          = {[64'hFFF0000000000001:64'hFFF7FFFFFFFFFFFF]};
        bins posrandom        = {64'h5A392534A57711AD};
        bins negrandom        = {64'hA6E895993737426C};
    }

    cr_fs1_edges_frm_D : cross cp_fs1_edges_D,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 (double precision), FRM
    }
