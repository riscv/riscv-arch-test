    //////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_ff_load
    //////////////////////////////////////////////////////////////////////////////////

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD
        // Custom coverpoints for Vector fault-first load exception operations

        mask_disabled: coverpoint ins.current.insn[25] {
            bins disabled = {1'b1};
        }

        rs1_eq_0: coverpoint unsigned'(ins.current.rs1_val) {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS_LOAD};
        }

        cp_exceptionsv_ffLS_first_elm_trap : cross std_trap_vec, mask_disabled, rs1_eq_0;
    `endif

    //// end cp_exceptionsv_ff_load ////////////////////////////////////////////////
