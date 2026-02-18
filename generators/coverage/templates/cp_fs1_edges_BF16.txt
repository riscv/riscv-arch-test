    cp_fs1_edges_BF16 : coverpoint unsigned'(ins.current.fs1_val[15:0])  iff (ins.trap == 0 )  {
        // FS1 edges
        bins pos0             = {32'h0000};
        bins neg0             = {32'h8000};
        bins pos1             = {32'h3f80};
        bins neg1             = {32'hbf80};
        bins pos1p5           = {32'h3fc0};
        bins neg1p5           = {32'hbfc0};
        bins pos2             = {32'h4000};
        bins neg2             = {32'hc000};
        bins posminnorm       = {32'h0080};
        bins negminnorm       = {32'h8080};
        bins posmaxnorm       = {32'h7f7f};
        bins negmaxnorm       = {32'hff7f};
        bins posmax_subnorm   = {32'h007f};
        bins negmax_subnorm   = {32'h807f};
        bins posmid_subnorm   = {32'h0040};
        bins negmid_subnorm   = {32'h8040};
        bins posmin_subnorm   = {32'h0000};
        bins negmin_subnorm   = {32'h8000};
        bins posinfinity      = {32'h7f80};
        bins neginfinity      = {32'hff80};
        bins posQNaN          = {[32'h7fc0:32'h7fff]};
        bins posSNaN          = {[32'h7f81:32'h7fbf]};
        bins negQNaN          = {[32'hffc0:32'hffff]};
        bins negSNaN          = {[32'hff81:32'hffbf]};
        bins posrandom        = {32'h7ef8};
        bins negrandom        = {32'h813d};
    }
