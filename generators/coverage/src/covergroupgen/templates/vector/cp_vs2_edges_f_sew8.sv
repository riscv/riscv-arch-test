    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs2_edges_f_sew8
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs2_edges_f_sew8 : coverpoint vs_edges_check(ins.hart, ins.issue, ins.current.vs2_val, "1")  iff (ins.trap == 0 )  {
        // Integer edges: at SEW=8 the only Vf instructions are Zvfh conversions from 8-bit integers
        bins zero       = {vs_zero      };   //  = {(`SEW){1'b0}},
        bins one        = {vs_one       };   //  = {(`SEW-1){1'b0}, {1'b1}},
        bins two        = {vs_two       };   //  = {(`SEW-2){1'b0}, {2'b10}},
        bins min        = {vs_min       };   //  = {{1'b1}, (`SEW-1){1'b0}},
        bins minp1      = {vs_minp1     };   //  = {{1'b1}, (`SEW-2){1'b0}, {1'b1}},
        bins max        = {vs_max       };   //  = {{1'b0}, (`SEW-1){1'b1}},
        bins maxm1      = {vs_maxm1     };   //  = {{1'b0}, (`SEW-2){1'b1}, {1'b0}},
        bins ones       = {vs_ones      };   //  = {(`SEW){1'b1}},
        bins onesm1     = {vs_onesm1    };   //  = {(`SEW-1){1'b1}, {1'b0}},
        bins walkodd    = {vs_walkodd   };   //  = {(`SEW/2){2'b10}},
        bins walkeven   = {vs_walkeven  };   //  = {(`SEW/2){2'b01}},
        bins random     = {vs_random    };   //  = {(SEW){random}}
    }

    //// end cp_vs2_edges_f_sew8////////////////////////////////////////////////
