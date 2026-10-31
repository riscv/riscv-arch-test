    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_lmul1max_sew64
    //////////////////////////////////////////////////////////////////////////////////

    cr_vl_lmul_lmul1max_sew64 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                    3'(vl_check(ins.hart, ins.issue))}  iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 3)  {
        // Cross coverage all legal LMULs for SEW = 64 and vl edges (1, random, vlmax)
        // vl = 1, VLMAX and a value in between for each LMUL. VLMAX = VLEN * LMUL / SEW must be
        // at least 2 for a distinct VLMAX and at least 3 for a value in between.
        // Value of VTYPE.vlmul (vector register grouping), SEW = 64
        `ifdef ZVL64B_SUPPORTED
            bins one_one = {6'b000_001};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins one_vlmax = {6'b000_010};
        `endif
        `ifdef ZVL256B_SUPPORTED
            bins one_legal = {6'b000_011};
        `endif
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_lmul1max_sew64////////////////////////////////////////////////
