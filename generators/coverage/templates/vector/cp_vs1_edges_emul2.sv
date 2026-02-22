//////////////////////////////////////////////////////////////////////////////////
    // cp_vs1_edges_emul2
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs1_edges_emul2 : coverpoint vs_edges_check(ins.hart, ins.issue, ins.current.vs1_val, "2")  iff (ins.trap == 0 )  {
        // Edges values of vs1 (emul = 2), assuming vl = 1
        bins zero       = {vs_zero      };   //  = {(`SEW){1'b0}},
        bins one        = {vs_one       };   //  = {(`SEW-1){1'b0}, {1'b1}},
        bins two        = {vs_two       };   //  = {(`SEW-2){1'b0}, {2'b10}},
        bins min        = {vs_min       };   //  = {{1'b1}, (`SEW-1){1'b0}},
        bins minp1      = {vs_minp1     };   //  = {{1'b1}, (`SEW-2){1'b0}, {1'b1}},
        bins max        = {vs_max       };   //  = {{1'b0}, (`SEW-1){1'b1}},
        bins maxm1      = {vs_maxm1     };   //  = {{1'b0}, (`SEW-2){1'b1}, {1'b0}},
        bins ones       = {vs_ones      };   //  = {(`SEW){1'b1}},
        bins onesm1     = {vs_onesm1    };   //  = {(`SEW-1){1'b1}, {1'b0}},
        bins walkodd    = {vs_walkeodd  };   //  = {(`SEW/2){2'b10}},
        bins walkeven   = {vs_walkeven  };   //  = {(`SEW/2){2'b01}},
        bins random     = {vs_random    };   //  = {(SEW){random}}
    }

    //// end cp_vs1_edges_emul2////////////////////////////////////////////////
