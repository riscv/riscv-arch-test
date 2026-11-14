    //////////////////////////////////////////////////////////////////////////////////
    // cr_vl_lmul_egs4_sew64
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lmul_egs4_sew64 : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vlmul")  iff (ins.trap == 0 & get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew") == 3) {
        // LMUL values for EGS=4, SEW=64 instructions: LMUL * VLEN must be at least EGW = 256
        bins eight = {3};
        bins four = {2};
        `ifdef ZVL128B_SUPPORTED
            bins two = {1};
        `endif
        `ifdef ZVL256B_SUPPORTED
            bins one = {0};
        `endif
    }

    cr_vl_lmul_egs4_sew64 : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vlmul")[2:0],
                                         3'(vl_check(ins.hart, ins.issue, 4))}  iff (ins.trap == 0 & get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew") == 3)  {
        // LMUL crossed with vl = EGS, VLMAX and a value in between for EGS=4 instructions at SEW=64.
        // LMUL * VLEN must be at least EGW = 256, and VLMAX = VLEN * LMUL / SEW must hold at least two
        // element groups for a distinct VLMAX and four for a value in between.
        `ifdef ZVL256B_SUPPORTED
            bins one_one = {6'b000_001};
        `endif
        `ifdef ZVL512B_SUPPORTED
            bins one_vlmax = {6'b000_010};
        `endif
        `ifdef ZVL1024B_SUPPORTED
            bins one_legal = {6'b000_011};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins two_one = {6'b001_001};
        `endif
        `ifdef ZVL256B_SUPPORTED
            bins two_vlmax = {6'b001_010};
        `endif
        `ifdef ZVL512B_SUPPORTED
            bins two_legal = {6'b001_011};
        `endif
        `ifdef ZVL64B_SUPPORTED
            bins four_one = {6'b010_001};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins four_vlmax = {6'b010_010};
        `endif
        `ifdef ZVL256B_SUPPORTED
            bins four_legal = {6'b010_011};
        `endif
        bins eight_one = {6'b011_001};
        `ifdef ZVL64B_SUPPORTED
            bins eight_vlmax = {6'b011_010};
        `endif
        `ifdef ZVL128B_SUPPORTED
            bins eight_legal = {6'b011_011};
        `endif
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_vl_lmul_egs4_sew64////////////////////////////////////////////////
