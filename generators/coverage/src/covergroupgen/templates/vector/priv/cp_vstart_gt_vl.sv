    //////////////////////////////////////////////////////////////////////////////////
    // cp_vstart_gt_vl
    //////////////////////////////////////////////////////////////////////////////////

    cp_vstart_gt_vl: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) >  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) &
                                 `UDB_MXLEN'(get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) > get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART)){
        bins true = {1};
    }

    //// end cp_vstart_gt_vl////////////////////////////////////////////////
