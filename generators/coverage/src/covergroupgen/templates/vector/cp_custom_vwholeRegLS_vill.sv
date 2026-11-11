    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vwholeRegLS_vill
    //////////////////////////////////////////////////////////////////////////////////

    // Whole register LS ignores vtype — should not trap even with vill=1
    cp_custom_vwholeRegLS_vill: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 1 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
                        ins.trap == 0
                    } {
                        bins true = {1};
                    }

    //// end cp_custom_vwholeRegLS_vill////////////////////////////////////////////////
