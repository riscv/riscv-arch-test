    //////////////////////////////////////////////////////////////////////////////////
    // cp_mstatus_vs_off
    // A vector floating-point instruction must raise an illegal-instruction trap
    // when mstatus.VS == Off (V extension disabled). The cross pins mstatus.FS to
    // a non-Off value so the trap can only be attributed to VS being Off (not FS).
    //////////////////////////////////////////////////////////////////////////////////

    mstatus_vs_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins inactive = {0};
    }

    mstatus_fs_active_for_vs_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins active = {[1:3]};
    }

    cp_mstatus_vs_off : cross mstatus_vs_off, mstatus_fs_active_for_vs_off;

    //// end cp_mstatus_vs_off////////////////////////////////////////////////
