

    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_e8
    //////////////////////////////////////////////////////////////////////////////////

    cr_vl_lmul_e8_sew64 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                    3'(vl_check(ins.hart, ins.issue))}  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 3)  {
        // Cross coverage all legal LMULs (excluding LMUL = 8) for SEW = 8 and vl edges (1, random, vlmax)
        // vl = 1, VLMAX and a value in between for each LMUL. VLMAX = VLEN * LMUL / SEW must be
        // at least 2 for a distinct VLMAX and at least 3 for a value in between.
        // Value of VTYPE.vlmul (vector register grouping)

        `ifdef ZVL64B_SUPPORTED
            bins one_one = {6'b000_001};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins one_vlmax = {6'b000_010};
        `endif
        `ifdef ZVL256B_SUPPORTED
            bins one_legal = {6'b000_011};
        `endif
        bins two_one = {6'b001_001};
        `ifdef ZVL64B_SUPPORTED
            bins two_vlmax = {6'b001_010};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins two_legal = {6'b001_011};
        `endif
        bins four_one = {6'b010_001};
        bins four_vlmax = {6'b010_010};
        `ifdef ZVL64B_SUPPORTED
            bins four_legal = {6'b010_011};
        `endif
        bins eight_one = {6'b011_001};
        bins eight_vlmax = {6'b011_010};
        bins eight_legal = {6'b011_011};
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_e8_sew64////////////////////////////////////////////////
