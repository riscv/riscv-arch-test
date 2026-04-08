//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_indexed_emul_data_only
    //////////////////////////////////////////////////////////////////////////////////

    // Verify EMUL*NFIELDS <= 8 constraint applies to data group only, not index group
    // Test at data LMUL*NFIELDS = 8 boundary; index EMUL*NFIELDS may exceed 8
    // Combined check: nf_field from insn[31:29] paired with correct LMUL
    //   NF=2 (nf=001) at LMUL=4 (vlmul=2)
    //   NF=4 (nf=011) at LMUL=2 (vlmul=1)
    //   NF=8 (nf=111) at LMUL=1 (vlmul=0)

    nf_lmul_at_boundary: coverpoint {
        (ins.current.insn[31:29] == 3'b001 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2) |
        (ins.current.insn[31:29] == 3'b011 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 1) |
        (ins.current.insn[31:29] == 3'b111 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 0)
    }
    {
        bins boundary_hit = {1'b1};
    }

    cp_custom_indexed_emul_data_only: cross std_vec, nf_lmul_at_boundary;

    //// end cp_custom_indexed_emul_data_only////////////////////////////////////////////////
