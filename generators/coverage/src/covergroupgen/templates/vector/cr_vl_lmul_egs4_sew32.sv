    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_egs4_sew32
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_egs4_sew32 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 2) {
        // LMUL values for EGS=4, SEW=32 instructions (EGS*SEW = 128 bits per group)
        // LMUL=8/4/2: always valid since VLEN=64 (minimum) satisfies LMUL*VLEN >= 128 bits
        bins eight  = {3};
        bins four   = {2};
        bins two    = {1};
        // Smaller LMULs require larger VLEN so that >=2 element groups are possible
        `ifdef ZVL256B_SUPPORTED
            bins one    = {0};   // LMUL=1: needs VLEN>=256 for >=2 element groups
        `endif
        `ifdef ZVL512B_SUPPORTED
            `ifdef LMULf2_SUPPORTED
                bins half    = {7};   // LMUL=1/2: needs VLEN>=512
            `endif
        `endif
        `ifdef ZVL1024B_SUPPORTED
            `ifdef LMULf4_SUPPORTED
                bins quarter = {6};   // LMUL=1/4: needs VLEN>=1024
            `endif
        `endif
    }

    cp_csr_vl_edges_egs4 : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // Edge values of VL (vector length)
        bins one        = {vl_one       };
        bins vlmax      = {vl_vlmax     };
        bins legal      = {vl_legal     };
    }

    cr_vl_lmul_egs4_sew32 : cross cp_csr_vtype_lmul_egs4_sew32, cp_csr_vl_edges_egs4  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 2)  {
        // Cross coverage of LMUL and VL edges for EGS=4 instructions at SEW=32
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_egs4_sew32////////////////////////////////////////////////
