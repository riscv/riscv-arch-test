    cp_fs1_badNB_S_H : coverpoint unsigned'(ins.current.fs1_val[31:0])  iff (ins.trap == 0 )  {
        // "FS1 Bad NaNBox edges (half NaNBoxed to 32 bits)";
        bins pos0             = {32'h0000_0000};
        bins neg0             = {32'hfffe_8000};
        bins pos1             = {32'h7fff_3C00};
        bins neg1             = {32'hbeef_BC00};
        bins posminnorm       = {32'hfeff_0400};
        bins negminnorm       = {32'h0fff_8400};
        bins posmaxnorm       = {32'hefff_7BFF};
        bins negmaxnorm       = {32'hc0de_FBFF};
        bins posinfinity      = {32'h4f1a_7C00};
        bins neginfinity      = {32'h0fff_FC00};
        bins posQNaN          = {[32'hffef_7E00:32'hfeef_7FFF]};
        bins posSNaN          = {[32'ha1b2_7C01:32'h4fd7_7DFF]};
    }
