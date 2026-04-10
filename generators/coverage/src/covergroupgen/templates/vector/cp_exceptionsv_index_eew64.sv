    //////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_index_eew64
    //////////////////////////////////////////////////////////////////////////////////

    // Cover that an indexed load/store with EEW=64 > MAXINDEXEEW was attempted and trapped.
    // ins.current.insn[14:12] encodes the index EEW (000=8, 101=16, 110=32, 111=64).
    // Assign this coverpoint only to instructions with index EEW=64 (ei64 instructions).
    // Note: std_trap_vec is defined in cp_exceptionsv_LS (always present alongside this).

    `ifndef MAXINDEXEEW_GE64
    index_eew64 : coverpoint ins.current.insn[14:12] {
        bins e64 = {3'b111};
    }
    cp_exceptionsv_index_eew64 : cross std_trap_vec, index_eew64;
    `endif

    //// end cp_exceptionsv_index_eew64//////////////////////////////////////////////
