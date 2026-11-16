

    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_e32_emul2max
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_all_le_8_e32_emul2max : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vlmul"){
        // Value of VTYPE.vlmul (vector register grouping)
        `ifdef UDB_ELEN_64
            bins eighth  = {5};
        `endif
        bins fourth = {6};
        bins half   = {7};
        // lmul 1 not supported for sew = 8 eew =32
        // lmul 2 not supported for sew = 8 eew = 32
    }

    cp_csr_vl_edges : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // Edges values of VL (vector length)
        bins one        = {vl_one       };
        bins vlmax      = {vl_vlmax     };
        bins legal      = {vl_legal     };
    }

    cr_vl_lmul_e32_emul2max_sew8 : cross cp_csr_vtype_lmul_all_le_8_e32_emul2max, cp_csr_vl_edges  iff (ins.trap == 0 & get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew") == 0)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 8 and vl edges (1, random, vlmax)
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_e32_emul2max_sew8////////////////////////////////////////////////
