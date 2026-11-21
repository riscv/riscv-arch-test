    //////////////////////////////////////////////////////////////////////////////////
    // cp_vstart_vl_noop
    //////////////////////////////////////////////////////////////////////////////////

    // Test vd not updated when vstart >= vl
    cp_vstart_vl_noop : coverpoint (get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) >=
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) &
                                    ins.trap == 0) {
        bins true = {1'b1};
    }

        //// end cp_vstart_vl_noop////////////////////////////////////////////////
