    //////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_ffLS
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector fault-first load/store exception operations
    // Note: std_trap_vec is defined in cp_exceptionsv_LS (always present alongside ffLS)

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS

    mask_disabled: coverpoint ins.current.insn[25] {
        bins disabled = {1'b1};
    }

    rs1_at_fault_addr: coverpoint (unsigned'(ins.current.rs1_val) == `RVMODEL_ACCESS_FAULT_ADDRESS) {
        bins at_fault_addr = {1'b1};
    }

    cp_exceptionsv_ffLS_first_elm_trap : cross std_trap_vec, mask_disabled, rs1_at_fault_addr;

    `endif

    //// end cp_exceptionsv_ffLS////////////////////////////////////////////////
