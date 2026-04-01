    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vwholeRegLS_vill
    //////////////////////////////////////////////////////////////////////////////////

    // Whole register LS ignores vtype — should not trap even with vill=1
    cp_custom_vwholeRegLS_vill: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 1 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        ins.trap == 0
                    } {
                        bins true = {1};
                    }

    //// end cp_custom_vwholeRegLS_vill////////////////////////////////////////////////
