    //////////////////////////////////////////////////////////////////////////////////
    // std_trap_vec
    //////////////////////////////////////////////////////////////////////////////////

    std_trap_vec : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) != 0 &
                        get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    //// end std_trap_vec ////////////////////////////////////////////////
