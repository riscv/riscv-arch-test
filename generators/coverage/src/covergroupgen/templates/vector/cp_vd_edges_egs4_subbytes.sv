    //////////////////////////////////////////////////////////////////////////////////
    // cp_vd_edges_egs4_subbytes
    //////////////////////////////////////////////////////////////////////////////////

    cp_vd_edges_egs4_byte_0 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[7:0])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 0);
    }

    cp_vd_edges_egs4_byte_1 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[15:8])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 1);
    }

    cp_vd_edges_egs4_byte_2 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[23:16])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 2);
    }

    cp_vd_edges_egs4_byte_3 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[31:24])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 3);
    }

    cp_vd_edges_egs4_byte_4 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[39:32])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 4);
    }

    cp_vd_edges_egs4_byte_5 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[47:40])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 5);
    }

    cp_vd_edges_egs4_byte_6 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[55:48])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 6);
    }

    cp_vd_edges_egs4_byte_7 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[63:56])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 7);
    }

    cp_vd_edges_egs4_byte_8 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[71:64])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 8);
    }

    cp_vd_edges_egs4_byte_9 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[79:72])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 9);
    }

    cp_vd_edges_egs4_byte_10 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[87:80])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 10);
    }

    cp_vd_edges_egs4_byte_11 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[95:88])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 11);
    }

    cp_vd_edges_egs4_byte_12 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[103:96])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 12);
    }

    cp_vd_edges_egs4_byte_13 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[111:104])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 13);
    }

    cp_vd_edges_egs4_byte_14 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[119:112])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 14);
    }

    cp_vd_edges_egs4_byte_15 : coverpoint (ins.get_vr_val_lmul4(ins.current.vd)[127:120])
        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") == 2)  {
        bins subbyte[] = {[0:255]} with (item % 16 == 15);
    }

    //// end cp_vd_edges_egs4_subbytes ////////////////////////////////////////////////
