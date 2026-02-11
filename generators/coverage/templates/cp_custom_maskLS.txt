    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_maskLS
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector mask load/store operations

    v0_eq_1: coverpoint unsigned'(ins.current.v0_val) {
        bins one = {1};
    }

    rs1_at_fault_addr: coverpoint (unsigned'(ins.current.rs1_val) == `ACCESS_FAULT_ADDRESS) {
        bins not_fault_addr = {1'b1};
    }

    vl_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins one = {1};
    }

    vl_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins two = {2};
    }

    vstart_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") {
        bins one = {1};
    }

    no_trap : coverpoint (ins.trap == 0) {
        bins zero = {0};
    }

    v0_eq_2: coverpoint unsigned'(ins.current.v0_val) {
        bins two = {2};
    }

    cp_custom_maskLS_emul_ge_16             : cross std_vec, vtype_all_lmulgt1, vtype_all_sewgt8;
    cp_custom_maskLS_tail_no_exception      : cross std_vec, vtype_lmul_2, vl_1, mask_enabled, v0_eq_1, rs1_at_fault_addr;
    cp_custom_maskLS_prestart_no_exception  : cross vill_not_set, vtype_lmul_2, vl_2, vstart_1, mask_enabled, rs1_at_fault_addr, v0_eq_2, no_trap, v0_eq_2;

    //// end cp_custom_maskLS////////////////////////////////////////////////
