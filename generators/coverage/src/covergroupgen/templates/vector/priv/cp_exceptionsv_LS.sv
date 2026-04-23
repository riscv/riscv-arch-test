    //////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_LS
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector load/store exception operations

    std_trap_vec : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    //// end cp_exceptionsv_LS////////////////////////////////////////////////
