    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs2_edges_egs8
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs2_edges_egs8 : coverpoint vs_edges_check_sew32_egs8(ins.hart, ins.issue, ins.get_vr_val_lmul8(ins.current.vs2))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 3)  {
        // Edge values of vs2 (EGS=8), assuming vl = 8
        bins zero       = {vs_zero      };   //  = {(`EGS*SEW){1'b0}},
        bins ones       = {vs_ones      };   //  = {(`EGS*SEW){1'b1}},
        bins walkodd    = {vs_walkodd   };   //  = {(`EGS*SEW/2){2'b10}},
        bins walkeven   = {vs_walkeven  };   //  = {(`EGS*SEW/2){2'b01}},
        bins random     = {vs_random    };   //  = {(EGS*SEW){random}}
    }

    //// end cp_vs2_edges_egs8 ////////////////////////////////////////////////
