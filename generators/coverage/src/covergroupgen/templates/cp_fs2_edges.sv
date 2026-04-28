    cp_fs2_edges : coverpoint unsigned'(ins.current.fs2_val[31:0])  iff (ins.trap == 0 )  {
        // FS2 edges
        bins pos0             = {32'h00000000};
        bins neg0             = {32'h80000000};
        bins pos1             = {32'h3f800000};
        bins neg1             = {32'hbf800000};
        bins pos1p5           = {32'h3fc00000};
        bins neg1p5           = {32'hbfc00000};
        bins pos2             = {32'h40000000};
        bins neg2             = {32'hc0000000};
        bins posminnorm       = {32'h00800000};
        bins negminnorm       = {32'h80800000};
        bins posmaxnorm       = {32'h7f7fffff};
        bins negmaxnorm       = {32'hff7fffff};
        bins posmax_subnorm   = {32'h007fffff};
        bins negmax_subnorm   = {32'h807fffff};
        bins posmid_subnorm   = {32'h00400000};
        bins negmid_subnorm   = {32'h80400000};
        bins posmin_subnorm   = {32'h00000001};
        bins negmin_subnorm   = {32'h80000001};
        bins posinfinity      = {32'h7f800000};
        bins neginfinity      = {32'hff800000};
        bins posQNaN          = {[32'h7fc00000:32'h7fffffff]};
        bins posSNaN          = {[32'h7f800001:32'h7fbfffff]};
        bins negQNaN          = {[32'hffc00000:32'hffffffff]};
        bins negSNaN          = {[32'hff800001:32'hffbfffff]};
        bins posrandom        = {32'h7ef8654f};
        bins negrandom        = {32'h813d9ab0};
    }
