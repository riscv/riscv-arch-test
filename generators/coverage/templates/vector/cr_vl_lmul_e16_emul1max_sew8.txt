

    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_e16_emul1max
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_all_le_8_e16_emul1max : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"){
        // Value of VTYPE.vlmul (vector register grouping)
        `ifdef LMULf8_SUPPORTED
            bins eighth  = {5};
        `endif
        `ifdef LMULf4_SUPPORTED
            bins fourth = {6};
        `endif
        `ifdef LMULf2_SUPPORTED
            bins half   = {7};
        `endif
        `ifndef COVER_VX8
            bins one    = {0};
        `endif
    }

    cp_csr_vl_edges : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // Edges values of VL (vector length)
        bins one        = {vl_one       };
        bins vlmax      = {vl_vlmax     };
        bins legal      = {vl_legal     };
    }

    cr_vl_lmul_e16_emul1max_sew8 : cross cp_csr_vtype_lmul_all_le_8_e16_emul1max, cp_csr_vl_edges  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 0)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 8 and vl edges (1, random, vlmax)
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_e16_emul1max_sew8////////////////////////////////////////////////
