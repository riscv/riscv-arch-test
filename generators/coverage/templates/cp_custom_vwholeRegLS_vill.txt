//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vwholeRegLS_vill
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector whole register load and store operations



    cp_custom_vwholeRegLS_vill: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 1 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    } {
                        bins true = {1};
                    }

    //// cp_custom_vwholeRegLS_vill////////////////////////////////////////////////
