    //////////////////////////////////////////////////////////////////////////////////
    // cp_vd_edges_egs4
    //////////////////////////////////////////////////////////////////////////////////

    cp_vd_edges_egs4 : coverpoint vs_edges_check_sew32_egs4(ins.hart, ins.issue, ins.get_vr_val_lmul4(ins.current.vd))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        // Edge values of vd (EGS=4), assuming vl = 1
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

    //// end cp_vd_edges_egs4////////////////////////////////////////////////
