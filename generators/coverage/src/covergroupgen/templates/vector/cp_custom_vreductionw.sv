    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vreductionw_vd_vs1_emul_16
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector widening reduction operations

    // ensures vd updates
    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;
    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    cp_custom_vreductionw_vd_vs1_emul_16 :      cross std_vec, vtype_lmul_8;

    //// end cp_custom_vreductionw_vd_vs1_emul_16 ////////////////////////////////////////////////
