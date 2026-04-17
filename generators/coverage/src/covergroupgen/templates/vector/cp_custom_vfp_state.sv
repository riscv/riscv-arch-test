    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_state
    //
    // Spec: any vector FP instruction that modifies FP extension state
    // (an f register or an FP CSR) must set mstatus.FS to Dirty.
    // Lockstep with a reference model verifies mstatus.FS is correctly dirtied;
    // this coverpoint only confirms the setup conditions exist: the instruction
    // modified FP state while mstatus.FS was not already Dirty.
    //
    // Note: vfmv.f.s (the only user) never sets fflags, so only the
    // register-write path is covered here.
    //////////////////////////////////////////////////////////////////////////////////

    // f register modified (e.g. vfmv.f.s writes fd)
    fd_changed_value : coverpoint (ins.current.fd_val != ins.prev.fd_val) {
        bins target = {1};
    }

    // mstatus.FS before the instruction was not Dirty (Off=0, Initial=1, Clean=2)
    mstatus_fs_prev_not_dirty : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins not_dirty = {[0:2]};
    }

    cp_custom_vfp_register_state_mstatus_dirty : cross std_vec, fd_changed_value, mstatus_fs_prev_not_dirty;

    //// end cp_custom_vfp_state////////////////////////////////////////////////
