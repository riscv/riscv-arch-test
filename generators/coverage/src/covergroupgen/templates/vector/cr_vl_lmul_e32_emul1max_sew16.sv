

    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_e32_emul1max
    //////////////////////////////////////////////////////////////////////////////////

    cr_vl_lmul_e32_emul1max_sew16 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                    3'(vl_check(ins.hart, ins.issue))}  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 1)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 8 and vl edges (1, random, vlmax)
        // vl = 1, VLMAX and a value in between for each LMUL. VLMAX = VLEN * LMUL / SEW must be
        // at least 2 for a distinct VLMAX and at least 3 for a value in between.
        // Value of VTYPE.vlmul (vector register grouping)
        `ifdef UDB_ELEN_64
            `ifdef ZVL64B_SUPPORTED
                bins fourth_one = {6'b110_001};
            `endif
            `ifdef ZVL128B_SUPPORTED
                bins fourth_vlmax = {6'b110_010};
            `endif
            `ifdef ZVL256B_SUPPORTED
                bins fourth_legal = {6'b110_011};
            `endif
        `endif
        bins half_one = {6'b111_001};
        `ifdef ZVL64B_SUPPORTED
            bins half_vlmax = {6'b111_010};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins half_legal = {6'b111_011};
        `endif
        // lmul 1 not supported for sew = 16 eew=32

    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_e32_emul1max_sew16////////////////////////////////////////////////
