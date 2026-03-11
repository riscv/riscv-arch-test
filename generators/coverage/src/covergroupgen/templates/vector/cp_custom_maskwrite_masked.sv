//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vmask_write_v0_masked
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector mask producing/writing operations where masked CAN be enabled

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

    vd_v0: coverpoint ins.current.insn[11:7] {
        bins zero = {5'b00000};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins enabled = {1'b0};
    }

    cp_custom_vmask_write_lmulge1:      cross std_vec, vtype_all_lmulge1, vl_max;
    cp_custom_vmask_write_v0_masked:    cross std_vec, vd_v0, mask_enabled;

    //// end cp_custom_vmask_write_v0_masked////////////////////////////////////////////////
