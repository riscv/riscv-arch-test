//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_indexed_emul_data_only
    //////////////////////////////////////////////////////////////////////////////////

    // Verify EMUL*NFIELDS <= 8 constraint applies to data group only, not index group
    // Test at LMUL*NFIELDS = 8 boundary; index EMUL*NFIELDS may exceed 8

    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    // NFIELDS from nf field (bits [31:29]), NFIELDS = nf + 1
    nf_8: coverpoint ins.current.insn[31:29] {
        bins nf7 = {3'b111};  // NFIELDS=8
    }

    nf_4: coverpoint ins.current.insn[31:29] {
        bins nf3 = {3'b011};  // NFIELDS=4
    }

    nf_2: coverpoint ins.current.insn[31:29] {
        bins nf1 = {3'b001};  // NFIELDS=2
    }

    // LMUL values paired with NFIELDS at the data EMUL*NFIELDS = 8 boundary
    vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins four = {2};
    }

    // LMUL*NFIELDS = 8 boundary cases (data EMUL at limit)
    cp_custom_indexed_emul_data_only_lmul1_nf8: cross std_vec, vtype_lmul_1, nf_8;
    cp_custom_indexed_emul_data_only_lmul2_nf4: cross std_vec, vtype_lmul_2, nf_4;
    cp_custom_indexed_emul_data_only_lmul4_nf2: cross std_vec, vtype_lmul_4, nf_2;

    //// end cp_custom_indexed_emul_data_only////////////////////////////////////////////////
