    cp_fs1_edges_H : coverpoint unsigned'(ins.current.fs1_val[15:0])  iff (ins.trap == 0 )  {
        // FS1 edges (Half Precision)
        bins pos0             = {16'h0000};
        bins neg0             = {16'h8000};
        bins pos1             = {16'h3C00};
        bins neg1             = {16'hBC00};
        bins pos1p5           = {16'h3E00};
        bins neg1p5           = {16'hBE00};
        bins pos2             = {16'h4000};
        bins neg2             = {16'hC000};
        bins posminnorm       = {16'h0400};
        bins negminnorm       = {16'h8400};
        bins posmaxnorm       = {16'h7BFF};
        bins negmaxnorm       = {16'hFBFF};
        bins posmax_subnorm   = {16'h03FF};
        bins negmax_subnorm   = {16'h83FF};
        bins posmid_subnorm   = {16'h0200};
        bins negmid_subnorm   = {16'h8200};
        bins posmin_subnorm   = {16'h0001};
        bins negmin_subnorm   = {16'h8001};
        bins posinfinity      = {16'h7C00};
        bins neginfinity      = {16'hFC00};
        bins posQNaN          = {[16'h7E00:16'h7FFF]};
        bins posSNaN          = {[16'h7C01:16'h7DFF]};
        bins negQNaN          = {[16'hFE00:16'hFFFF]};
        bins negSNaN          = {[16'hFC01:16'hFDFF]};
        bins posrandom        = {16'h58B4};
        bins negrandom        = {16'hC93A};
    }

    cr_fs1_edges_frm_H : cross cp_fs1_edges_H,cp_frm_2  iff (ins.trap == 0 )  {
        // Cross coverage FS1 (half precision), FRM
    }
