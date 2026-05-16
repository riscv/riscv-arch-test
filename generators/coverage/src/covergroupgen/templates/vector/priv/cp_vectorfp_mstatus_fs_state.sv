    //////////////////////////////////////////////////////////////////////////////////
    // cp_vectorfp_mstatus_fs_state
    // Sample the vector-FP instruction under each non-Off mstatus.FS starting
    // state (Initial=1, Clean=2, Dirty=3) with mstatus.VS != Off. We cannot
    // observe the FS state transition directly (legal impls may hard-wire FS to
    // Dirty), so this coverpoint only ensures the test exercises every starting
    // FS state. Combined with signature-based cross-model checking, this catches
    // transitioning-model bugs.
    //////////////////////////////////////////////////////////////////////////////////

    mstatus_fs_state : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins fs_initial = {1};
        bins fs_clean   = {2};
        bins fs_dirty   = {3};
    }

    mstatus_vs_active_for_fs_state : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active = {[1:3]};
    }

    cp_vectorfp_mstatus_fs_state : cross mstatus_fs_state, mstatus_vs_active_for_fs_state;

    //// end cp_vectorfp_mstatus_fs_state////////////////////////////////////////////////
