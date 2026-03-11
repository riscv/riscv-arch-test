//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vmask_write_lmulge1
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector mask producing/writing operations where masked CANNOT be enabled

    // ensures vd updates
    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;


    vtype_all_lmulge1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                        == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }

    cp_custom_vmask_write_lmulge1:      cross std_vec, vtype_all_lmulge1, vl_max;

    //// end cp_custom_vmask_write_lmulge1////////////////////////////////////////////////
