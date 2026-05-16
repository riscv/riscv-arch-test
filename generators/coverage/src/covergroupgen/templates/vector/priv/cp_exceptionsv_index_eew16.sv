    //////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_index_eew16
    //////////////////////////////////////////////////////////////////////////////////

    // Cover that an indexed load/store with EEW=16 > MAXINDEXEEW was attempted and trapped.
    // ins.current.insn[14:12] encodes the index EEW (000=8, 101=16, 110=32, 111=64).
    // Assign this coverpoint only to instructions with index EEW=16 (ei16 instructions).
    // Note: std_trap_vec is defined in cp_exceptionsv_LS (always present alongside this).

    `ifndef MAXINDEXEEW_GE16
    index_eew16 : coverpoint ins.current.insn[14:12] {
        bins e16 = {3'b101};
    }
    cp_exceptionsv_index_eew16 : cross std_trap_vec, index_eew16;
    `endif

    //// end cp_exceptionsv_index_eew16//////////////////////////////////////////////
