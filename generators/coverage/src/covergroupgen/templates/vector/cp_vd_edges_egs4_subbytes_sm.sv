    //////////////////////////////////////////////////////////////////////////////////
    // cp_vd_edges_egs4_subbytes_sm
    //////////////////////////////////////////////////////////////////////////////////

    // First sm4_subword call in vsm4r: B = x1 ^ x2 ^ x3 ^ rk0
    //   x0..x3 = vd words 0..3 = vd[31:0], vd[63:32], vd[95:64], vd[127:96]
    //   rk0..rk3 = vs2 words 0..3; rk0 = vs2[31:0]
    cp_vd_edges_egs4_sm_byte_0 : coverpoint (shangmi_round_subbyte(ins.get_vr_val_lmul4(ins.current.vd), ins.get_vr_val_lmul4(ins.current.vs2), 0))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 4 == 0);
    }

    cp_vd_edges_egs4_sm_byte_1 : coverpoint (shangmi_round_subbyte(ins.get_vr_val_lmul4(ins.current.vd), ins.get_vr_val_lmul4(ins.current.vs2), 1))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 4 == 1);
    }

    cp_vd_edges_egs4_sm_byte_2 : coverpoint (shangmi_round_subbyte(ins.get_vr_val_lmul4(ins.current.vd), ins.get_vr_val_lmul4(ins.current.vs2), 2))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 4 == 2);
    }

    cp_vd_edges_egs4_sm_byte_3 : coverpoint (shangmi_round_subbyte(ins.get_vr_val_lmul4(ins.current.vd), ins.get_vr_val_lmul4(ins.current.vs2), 3))
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 4 == 3);
    }

    //// end cp_vd_edges_egs4_subbytes_sm ////////////////////////////////////////////////
