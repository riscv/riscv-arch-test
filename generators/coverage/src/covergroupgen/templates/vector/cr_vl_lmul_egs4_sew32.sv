    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_egs4_sew32
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_egs4_sew32 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 2) {
        // LMUL values for EGS=4, SEW=32 instructions (EGS*SEW = 128 bits per group)
        // LMUL=8/4/2: always valid since VLEN=64 (minimum) satisfies LMUL*VLEN >= 128 bits
        bins eight  = {3};
        bins four   = {2};
        `ifdef ZVL64B_SUPPORTED
            bins two    = {1};
        `endif
        // Smaller LMULs require larger VLEN so that >=2 element groups are possible
        `ifdef ZVL128B_SUPPORTED
            bins one    = {0};   // LMUL=1: needs VLEN>=256 for >=2 element groups
        `endif
        `ifdef ZVL256B_SUPPORTED
            `ifdef LMULf2_SUPPORTED
                bins half    = {7};   // LMUL=1/2: needs VLEN>=512
            `endif
        `endif
    }

    cp_csr_vl_edges_egs4 : coverpoint vl_check(ins.hart, ins.issue, 4)  iff (ins.trap == 0 )  {
        // Edge values of VL (vector length)
        bins vl_four     = {vl_one      };
        bins vlmax      = {vl_vlmax     };
        bins vl_legal      = {vl_legal     };
    }

    cr_vl_lmul_egs4_sew32 : cross cp_csr_vtype_lmul_egs4_sew32, cp_csr_vl_edges_egs4  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 2)  {
        // Cross coverage of LMUL and VL edges for EGS=4 instructions at SEW=32
        `ifdef ZVL256B_SUPPORTED
            `ifndef ZVL512B_SUPPORTED
                // In this case, there is exactly one valid vl, vl_legal is covered by the next ifndef
                ignore_bins vlfour_eq_vlmax_lmulf2 = binsof(cp_csr_vtype_lmul_egs4_sew32.half) && binsof(cp_csr_vl_edges_egs4.vlmax);
            `endif
            `ifndef ZVL1024B_SUPPORTED
                // In this case, there are two valid vls, so vl_legal is not possible to hit
                ignore_bins impossible_vl_legal_lmulf2 = binsof(cp_csr_vtype_lmul_egs4_sew32.half) && binsof(cp_csr_vl_edges_egs4.vl_legal);
            `endif
        `endif
        `ifdef ZVL128B_SUPPORTED
            `ifndef ZVL256B_SUPPORTED
                // In this case, there is exactly one valid vl, vl_legal is covered by the next ifndef
                ignore_bins vlfour_eq_vlmax_lmul1 = binsof(cp_csr_vtype_lmul_egs4_sew32.one) && binsof(cp_csr_vl_edges_egs4.vlmax);
            `endif
            `ifndef ZVL512B_SUPPORTED
                // In this case, there are two valid vls, so vl_legal is not possible to hit
                ignore_bins impossible_vl_legal_lmul1 = binsof(cp_csr_vtype_lmul_egs4_sew32.one) && binsof(cp_csr_vl_edges_egs4.vl_legal);
            `endif
        `endif
        `ifdef ZVL64B_SUPPORTED
            `ifndef ZVL128B_SUPPORTED
                // In this case, there is exactly one valid vl, vl_legal is covered by the next ifndef
                ignore_bins vlfour_eq_vlmax_lmul2 = binsof(cp_csr_vtype_lmul_egs4_sew32.two) && binsof(cp_csr_vl_edges_egs4.vlmax);
            `endif
            `ifndef ZVL256B_SUPPORTED
                // In this case, there are two valid vls, so vl_legal is not possible to hit
                ignore_bins impossible_vl_legal_lmul2 = binsof(cp_csr_vtype_lmul_egs4_sew32.two) && binsof(cp_csr_vl_edges_egs4.vl_legal);
            `endif
        `endif
        `ifdef ZVL32B_SUPPORTED
            `ifndef ZVL64B_SUPPORTED
                // In this case, there is exactly one valid vl, vl_legal is covered by the next ifndef
                ignore_bins vlfour_eq_vlmax_lmul4 = binsof(cp_csr_vtype_lmul_egs4_sew32.four) && binsof(cp_csr_vl_edges_egs4.vlmax);
            `endif
            `ifndef ZVL128B_SUPPORTED
                // In this case, there are two valid vls, so vl_legal is not possible to hit
                ignore_bins impossible_vl_legal_lmul4 = binsof(cp_csr_vtype_lmul_egs4_sew32.four) && binsof(cp_csr_vl_edges_egs4.vl_legal);
            `endif
        `endif
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_egs4_sew32////////////////////////////////////////////////
