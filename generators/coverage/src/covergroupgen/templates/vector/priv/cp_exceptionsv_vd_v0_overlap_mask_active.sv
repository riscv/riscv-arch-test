

    vd_v0 : coverpoint ins.current.insn[11:7] {
        bin zero = {0};
    }

    cp_exceptionsv_vd_v0_overlap_mask_active : cross std_trap_vec, vd_v0, mask_enabled;
