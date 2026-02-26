    cp_fs3_badNB_D_H : coverpoint unsigned'(ins.current.fs3_val[63:0])  iff (ins.trap == 0 )  {
        // "FS3 Bad NaNBox edges (half NaNBoxed to 64 bits)";
        bins pos0             = {64'hffffffff0000_0000};
        bins neg0             = {64'hfffffffffffe_8000};
        bins pos1             = {64'h7fffffffffff_3C00};
        bins neg1             = {64'hfeedbee5beef_BC00};
        bins posminnorm       = {64'hffffffefffff_0400};
        bins negminnorm       = {64'h00000000ffff_8400};
        bins posmaxnorm       = {64'hefffffffffff_7BFF};
        bins negmaxnorm       = {64'hc0dec0dec0de_FBFF};
        bins posinfinity      = {64'ha83ef1cc4f1a_7C00};
        bins neginfinity      = {64'hffffffff0fff_FC00};
        bins posQNaN          = {[64'hfffeffffffff_7E00:64'hffffffefffff_7FFF]};
        bins posSNaN          = {[64'ha1b2c3d4e5f6_7C01:64'hfffffffcffff_7DFF]};
    }
