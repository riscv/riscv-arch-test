    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ffLS
    //////////////////////////////////////////////////////////////////////////////////

    // Fault-only-first load: fault on non-first element updates VL without trapping

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
    v0_eq_1: coverpoint unsigned'(ins.current.v0_val) {
        bins one = {1};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b0};
    }

    rs1_at_fault_addr: coverpoint (unsigned'(ins.current.rs1_val) == `RVMODEL_ACCESS_FAULT_ADDRESS) {
        bins not_fault_addr = {1'b1};
    }

    cp_custom_ffLS_update_vl : cross std_vec, vtype_lmul_2, vl_max, mask_enabled, v0_eq_1, rs1_at_fault_addr;
    `endif

    //// end cp_custom_ffLS////////////////////////////////////////////////
