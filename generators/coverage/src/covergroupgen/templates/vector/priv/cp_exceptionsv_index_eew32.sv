    //////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_index_eew32
    //////////////////////////////////////////////////////////////////////////////////

    // Cover that an indexed load/store with EEW=32 > MAXINDEXEEW was attempted and trapped.
    // ins.current.insn[14:12] encodes the index EEW (000=8, 101=16, 110=32, 111=64).
    // Assign this coverpoint only to instructions with index EEW=32 (ei32 instructions).
    // Note: std_trap_vec is defined in cp_exceptionsv_LS (always present alongside this).

    `ifndef MAXINDEXEEW_GE32
    index_eew32 : coverpoint ins.current.insn[14:12] {
        bins e32 = {3'b110};
    }
    cp_exceptionsv_index_eew32 : cross std_trap_vec, index_eew32;
    `endif

    //// end cp_exceptionsv_index_eew32//////////////////////////////////////////////
