    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_lmul1max_sew64
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_all_sew64_lmul_le_1 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 3) {
        // Value of VTYPE.vlmul (vector register grouping), SEW = 64
        bins one    = {0};
    }

    cp_csr_vl_edges : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // Edges values of VL (vector length)
        bins one        = {vl_one       };
        bins vlmax      = {vl_vlmax     };
        bins legal      = {vl_legal     };
    }

    cr_vl_lmul_lmul1max_sew64 : cross cp_csr_vtype_lmul_all_sew64_lmul_le_1, cp_csr_vl_edges  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 3)  {
        // Cross coverage all legal LMULs for SEW = 64 and vl edges (1, random, vlmax)
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_lmul1max_sew64////////////////////////////////////////////////
