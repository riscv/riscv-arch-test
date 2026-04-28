    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_sew64_lmul4max
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_all_lmul4max_sew64_lmul_le_4 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 3) {
        // Value of VTYPE.vlmul (vector register grouping), SEW = 64, excluding LMUL = 8
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
    }

    cp_csr_vl_edges : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // Edges values of VL (vector length)
        bins one        = {vl_one       };
        bins vlmax      = {vl_vlmax     };
        bins legal      = {vl_legal     };
    }

    cr_vl_lmul_lmul4max_sew64 : cross cp_csr_vtype_lmul_all_lmul4max_sew64_lmul_le_4, cp_csr_vl_edges  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 3)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 64 and vl edges (1, random, vlmax)
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_lmul4max_sew64////////////////////////////////////////////////
