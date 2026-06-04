    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs1_edges_egs4
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs1_edges_egs4 : coverpoint vs_edges_check_egs4(ins.hart, ins.issue, ins.get_vr_val_lmul4(ins.current.vs1))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        // Edge values of vs1 (EGS=4), assuming vl = 4
        bins zero       = {vs_zero      };   //  = {(`EGS*SEW){1'b0}},
        bins ones       = {vs_ones      };   //  = {(`EGS*SEW){1'b1}},
        bins walkodd    = {vs_walkodd   };   //  = {(`EGS*SEW/2){2'b10}},
        bins walkeven   = {vs_walkeven  };   //  = {(`EGS*SEW/2){2'b01}},
        bins random     = {vs_random    };   //  = {(EGS*SEW){random}}
    }

    //// end cp_vs1_edges_egs4////////////////////////////////////////////////
