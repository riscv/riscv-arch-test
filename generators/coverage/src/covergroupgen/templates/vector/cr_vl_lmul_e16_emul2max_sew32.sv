

    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_e16_emul2max
    //////////////////////////////////////////////////////////////////////////////////

    cr_vl_lmul_e16_emul2max_sew32 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                    3'(vl_check(ins.hart, ins.issue))}  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 2)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 8 and vl edges (1, random, vlmax)
        // vl = 1, VLMAX and a value in between for each LMUL. VLMAX = VLEN * LMUL / SEW must be
        // at least 2 for a distinct VLMAX and at least 3 for a value in between.
        // Value of VTYPE.vlmul (vector register grouping)
        `ifdef UDB_ELEN_64
            `ifdef ZVL64B_SUPPORTED
                bins half_one = {6'b111_001};
            `endif
            `ifdef ZVL128B_SUPPORTED
                bins half_vlmax = {6'b111_010};
            `endif
            `ifdef ZVL256B_SUPPORTED
                bins half_legal = {6'b111_011};
            `endif
        `endif
        bins one_one = {6'b000_001};
        `ifdef ZVL64B_SUPPORTED
            bins one_vlmax = {6'b000_010};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins one_legal = {6'b000_011};
        `endif
        bins two_one = {6'b001_001};
        bins two_vlmax = {6'b001_010};
        `ifdef ZVL64B_SUPPORTED
            bins two_legal = {6'b001_011};
        `endif
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_e16_emul2max_sew32////////////////////////////////////////////////
