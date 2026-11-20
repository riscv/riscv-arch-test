    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_sew8
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_all_sew8_lmul_le_8 : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vlmul")  iff (ins.trap == 0 & get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew") == 0) {
        // Value of VTYPE.vlmul (vector register grouping), SEW = 8
        `ifdef UDB_ELEN_64
            bins eighth  = {5};
        `endif
        bins fourth = {6};
        bins half   = {7};
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

    cr_vl_lmul_sew8 : cross cp_csr_vtype_lmul_all_sew8_lmul_le_8, cp_csr_vl_edges {
        // Cross coverage all legal LMULs for SEW = 8 and vl edges (1, random, vlmax)
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_sew8////////////////////////////////////////////////
