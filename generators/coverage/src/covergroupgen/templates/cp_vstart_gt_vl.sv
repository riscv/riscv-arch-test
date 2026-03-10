//////////////////////////////////////////////////////////////////////////////////
    // cp_vstart_gt_vl
    //////////////////////////////////////////////////////////////////////////////////

    cp_vstart_gt_vl: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") &
                                 get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE) > get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart")){
        bins true = {1};
    }

    //// end cp_vstart_gt_vl////////////////////////////////////////////////
