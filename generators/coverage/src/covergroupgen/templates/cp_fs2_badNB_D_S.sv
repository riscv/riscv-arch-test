    cp_fs2_badNB_D_S : coverpoint unsigned'(ins.current.fs2_val[63:0])  iff (ins.trap == 0 )  {
        // "FS2 Bad NaNBox edges (single NaNBoxed to 64 bits)";
        bins pos0             = {64'hffffefff_00000000};
        bins neg0             = {64'haaaaaaaa_80000000};
        bins pos1             = {64'h00000000_3f800000};
        bins neg1             = {64'hdeadbeef_bf800000};
        bins posminnorm       = {64'ha1b2c3d4_00800000};
        bins negminnorm       = {64'hffffffef_80800000};
        bins posmaxnorm       = {64'hfeffffef_7f7fffff};
        bins negmaxnorm       = {64'h7e7e7e7e_ff7fffff};
        bins posinfinity      = {64'h7fffffff_7f800000};
        bins neginfinity      = {64'hfffffffe_ff800000};
        bins posQNaN          = {[64'hfeedbee5_7fc00000:64'hffc0deff_7fffffff]};
        bins posSNaN          = {[64'hfeffffff_7f800001:64'hfffffeff_7fbfffff]};
    }
