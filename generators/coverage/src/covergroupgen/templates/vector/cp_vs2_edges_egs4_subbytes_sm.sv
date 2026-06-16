    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs2_edges_egs4_subbytes_sm
    //////////////////////////////////////////////////////////////////////////////////

    // First sm4_subword call in vsm4k: B = rk1 ^ rk2 ^ rk3 ^ ck(4*rnd)
    //   rk0..rk3 = vs2 words 0..3 = vs2[31:0], vs2[63:32], vs2[95:64], vs2[127:96]
    //   ck(4*rnd) is a fixed constant per round; excluded here as it only shifts values
    cp_vs2_edges_egs4_sm_byte_0 : coverpoint (shangmi_key_schedule_subbyte(ins.get_vr_val_lmul4(ins.current.vs2), ins.current.imm, 0))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 4 == 0);
    }

    cp_vs2_edges_egs4_sm_byte_1 : coverpoint (shangmi_key_schedule_subbyte(ins.get_vr_val_lmul4(ins.current.vs2), ins.current.imm, 1))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 4 == 1);
    }

    cp_vs2_edges_egs4_sm_byte_2 : coverpoint (shangmi_key_schedule_subbyte(ins.get_vr_val_lmul4(ins.current.vs2), ins.current.imm, 2))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 4 == 2);
    }

    cp_vs2_edges_egs4_sm_byte_3 : coverpoint (shangmi_key_schedule_subbyte(ins.get_vr_val_lmul4(ins.current.vs2), ins.current.imm, 3))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 4 == 3);
    }

    //// end cp_vs2_edges_egs4_subbytes_sm ////////////////////////////////////////////////
