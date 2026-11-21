    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_lmul1max_sew16
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_all_sew16_lmul_le_1 : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vlmul")  iff (ins.trap == 0 & get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew") == 1) {
        // Value of VTYPE.vlmul (vector register grouping), SEW = 16
        `ifdef LMULf4_SUPPORTED
            bins fourth = {6};
        `endif
        `ifdef LMULf2_SUPPORTED
            bins half   = {7};
        `endif
        bins one    = {0};
    }

    cp_csr_vl_edges : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // Edges values of VL (vector length)
        bins one        = {vl_one       };
        bins vlmax      = {vl_vlmax     };
        bins legal      = {vl_legal     };
    }

    cr_vl_lmul_lmul1max_sew16 : cross cp_csr_vtype_lmul_all_sew16_lmul_le_1, cp_csr_vl_edges  iff (ins.trap == 0 & get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew") == 1)  {
        // Cross coverage all legal LMULs for SEW = 16 and vl edges (1, random, vlmax)
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_lmul1max_sew16////////////////////////////////////////////////
