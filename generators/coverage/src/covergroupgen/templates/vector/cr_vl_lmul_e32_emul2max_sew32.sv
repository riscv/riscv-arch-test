

    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_e32_emul2max
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_all_le_8_e32_emul2max : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"){
        // Value of VTYPE.vlmul (vector register grouping)
        `ifdef LMULf2_SUPPORTED
            bins half   = {7};
        `endif
        bins one    = {0};
        bins two    = {1};
    }

    cp_csr_vl_edges : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // Edges values of VL (vector length)
        bins one        = {vl_one       };
        bins vlmax      = {vl_vlmax     };
        bins legal      = {vl_legal     };
    }

    cr_vl_lmul_e32_emul2max_sew32 : cross cp_csr_vtype_lmul_all_le_8_e32_emul2max, cp_csr_vl_edges  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 2)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 8 and vl edges (1, random, vlmax)
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_e32_emul2max_sew32////////////////////////////////////////////////
