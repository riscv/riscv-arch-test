

    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_e16
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_all_le_8_e16 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"){
        // Value of VTYPE.vlmul (vector register grouping)
        `ifdef LMULf4_SUPPORTED
            bins fourth = {6};
        `endif
        `ifdef LMULf2_SUPPORTED
            bins half   = {7};
        `endif
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_csr_vl_edges : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // Edges values of VL (vector length)
        bins one        = {vl_one       };
        bins vlmax      = {vl_vlmax     };
        bins legal      = {vl_legal     };
    }

    cr_vl_lmul_e16_sew16 : cross cp_csr_vtype_lmul_all_le_8_e16, cp_csr_vl_edges  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 1)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 8 and vl edges (1, random, vlmax)
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_e16_sew16////////////////////////////////////////////////
