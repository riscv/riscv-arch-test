

    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_e32_emul1max
    //////////////////////////////////////////////////////////////////////////////////

    cr_vl_lmul_e32_emul1max_sew8 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                    3'(vl_check(ins.hart, ins.issue))}  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 0)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 8 and vl edges (1, random, vlmax)
        // vl = 1, VLMAX and a value in between for each LMUL. VLMAX = VLEN * LMUL / SEW must be
        // at least 2 for a distinct VLMAX and at least 3 for a value in between.
        // Value of VTYPE.vlmul (vector register grouping)
        `ifdef UDB_ELEN_64
            `ifdef ZVL64B_SUPPORTED
                bins eighth_one = {6'b101_001};
            `endif
            `ifdef ZVL128B_SUPPORTED
                bins eighth_vlmax = {6'b101_010};
            `endif
            `ifdef ZVL256B_SUPPORTED
                bins eighth_legal = {6'b101_011};
            `endif
        `endif
        bins fourth_one = {6'b110_001};
        `ifdef ZVL64B_SUPPORTED
            bins fourth_vlmax = {6'b110_010};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins fourth_legal = {6'b110_011};
        `endif

        // half not supported for sew=8 eew=32
        // one not supported for sew =8 eew = 32
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_e32_emul1max_sew8////////////////////////////////////////////////
