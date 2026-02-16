    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ffLS_update_vl
    //////////////////////////////////////////////////////////////////////////////////

    // Fault-only-first load: fault on non-first element updates VL without trapping

    v0_eq_1: coverpoint unsigned'(ins.current.v0_val) {
        bins one = {1};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b0};
    }

    rs1_at_fault_addr: coverpoint (unsigned'(ins.current.rs1_val) == `RVMODEL_ACCESS_FAULT_ADDRESS) {
        bins not_fault_addr = {1'b1};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                        == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }

    cp_custom_ffLS_update_vl : cross std_vec, vtype_lmul_2, vl_max, mask_enabled, v0_eq_1, rs1_at_fault_addr;

    //// end cp_custom_ffLS_update_vl////////////////////////////////////////////////
