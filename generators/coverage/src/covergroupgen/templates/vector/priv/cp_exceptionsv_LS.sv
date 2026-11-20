    //////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_LS
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector load/store exception operations

    std_trap_vec : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) != 0 &
                        get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    //// end cp_exceptionsv_LS////////////////////////////////////////////////
