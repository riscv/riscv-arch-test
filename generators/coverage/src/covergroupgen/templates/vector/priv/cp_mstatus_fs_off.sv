    //////////////////////////////////////////////////////////////////////////////////
    // cp_mstatus_fs_off
    // A vector floating-point instruction must raise an illegal-instruction trap
    // when mstatus.FS == Off (FP extension disabled). The cross pins mstatus.VS to
    // a non-Off value so the trap can only be attributed to FS being Off (not VS).
    //////////////////////////////////////////////////////////////////////////////////

    mstatus_fs_off : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "fs") {
        bins inactive = {0};
    }

    mstatus_vs_active_for_fs_off : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_MSTATUS, "vs") {
        bins active = {[1:3]};
    }

    cp_mstatus_fs_off : cross mstatus_fs_off, mstatus_vs_active_for_fs_off;

    //// end cp_mstatus_fs_off////////////////////////////////////////////////
