    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_egs8_sew32
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_egs8_sew32 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 2) {
        // LMUL values for EGS=8, SEW=32 instructions (EGS*SEW = 256 bits per group)
        // LMUL=8: always valid since VLEN=32 (minimum) satisfies LMUL*VLEN >= 256 bits
        bins eight  = {3};
        `ifdef ZVL64B_SUPPORTED
            bins four   = {2};   // LMUL=4: needs VLEN>=64 for valid configuration
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins two    = {1};   // LMUL=2: needs VLEN>=128
        `endif
        `ifdef ZVL256B_SUPPORTED
            bins one    = {0};   // LMUL=1: needs VLEN>=256 for >=2 element groups
        `endif
        `ifdef ZVL512B_SUPPORTED
            `ifdef LMULf2_SUPPORTED
                bins half    = {7};   // LMUL=1/2: needs VLEN>=512
            `endif
        `endif
    }

    cp_csr_vl_edges_egs8 : coverpoint vl_check(ins.hart, ins.issue, 8)  iff (ins.trap == 0 )  {
        // Edge values of VL (vector length)
        bins vl_eight    = {vl_one      };
        bins vlmax       = {vl_vlmax    };
        bins vl_legal    = {vl_legal    };
    }

    cr_vl_lmul_egs8_sew32 : cross cp_csr_vtype_lmul_egs8_sew32, cp_csr_vl_edges_egs8  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 2)  {
        // Cross coverage of LMUL and VL edges for EGS=8 instructions at SEW=32
        `ifdef ZVL512B_SUPPORTED
            `ifndef ZVL1024B_SUPPORTED
                ignore_bins vleight_eq_vlmax_lmulf2 = binsof(cp_csr_vtype_lmul_egs8_sew32.half) && binsof(cp_csr_vl_edges_egs8.vlmax);
            `endif
            `ifndef ZVL2048B_SUPPORTED
                ignore_bins impossible_vl_legal_lmulf2 = binsof(cp_csr_vtype_lmul_egs8_sew32.half) && binsof(cp_csr_vl_edges_egs8.vl_legal);
            `endif
        `endif
        `ifdef ZVL256B_SUPPORTED
            `ifndef ZVL512B_SUPPORTED
                ignore_bins vleight_eq_vlmax_lmul1 = binsof(cp_csr_vtype_lmul_egs8_sew32.one) && binsof(cp_csr_vl_edges_egs8.vlmax);
            `endif
            `ifndef ZVL1024B_SUPPORTED
                ignore_bins impossible_vl_legal_lmul1 = binsof(cp_csr_vtype_lmul_egs8_sew32.one) && binsof(cp_csr_vl_edges_egs8.vl_legal);
            `endif
        `endif
        `ifdef ZVL128B_SUPPORTED
            `ifndef ZVL256B_SUPPORTED
                ignore_bins vleight_eq_vlmax_lmul2 = binsof(cp_csr_vtype_lmul_egs8_sew32.two) && binsof(cp_csr_vl_edges_egs8.vlmax);
            `endif
            `ifndef ZVL512B_SUPPORTED
                ignore_bins impossible_vl_legal_lmul2 = binsof(cp_csr_vtype_lmul_egs8_sew32.two) && binsof(cp_csr_vl_edges_egs8.vl_legal);
            `endif
        `endif
        `ifdef ZVL64B_SUPPORTED
            `ifndef ZVL128B_SUPPORTED
                ignore_bins vleight_eq_vlmax_lmul4 = binsof(cp_csr_vtype_lmul_egs8_sew32.four) && binsof(cp_csr_vl_edges_egs8.vlmax);
            `endif
            `ifndef ZVL256B_SUPPORTED
                ignore_bins impossible_vl_legal_lmul4 = binsof(cp_csr_vtype_lmul_egs8_sew32.four) && binsof(cp_csr_vl_edges_egs8.vl_legal);
            `endif
        `endif
        `ifdef ZVL32B_SUPPORTED
            `ifndef ZVL64B_SUPPORTED
                ignore_bins vleight_eq_vlmax_lmul8 = binsof(cp_csr_vtype_lmul_egs8_sew32.eight) && binsof(cp_csr_vl_edges_egs8.vlmax);
            `endif
            `ifndef ZVL128B_SUPPORTED
                ignore_bins impossible_vl_legal_lmul8 = binsof(cp_csr_vtype_lmul_egs8_sew32.eight) && binsof(cp_csr_vl_edges_egs8.vl_legal);
            `endif
        `endif
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_egs8_sew32 ////////////////////////////////////////////////
