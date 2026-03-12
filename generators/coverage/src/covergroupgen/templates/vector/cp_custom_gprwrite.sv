//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_gprWriting_vstart_eq_vl
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector gpr writing instructions (instructions with rd)

    vtype_prev_vill_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins vill_not_set = {0};
    }

    vstart_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") {
        bins target = {0};
    }

    no_trap: coverpoint (ins.trap == 0) {
        bins true = {1'b1};
    }

    vl_0 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins zero = {0};
    }

    cp_custom_gprWriting_vstart_eq_vl : cross vtype_prev_vill_clear, vstart_zero, no_trap, vl_0;

    //// end cp_custom_gprWriting_vstart_eq_vl////////////////////////////////////////////////
