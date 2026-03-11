    // Custom coverpoints for Vector narrowing operations

    vs1_vd_overlap_lmul1: coverpoint (ins.current.insn[19:16] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }

    vd_even: coverpoint ins.current.insn[7] {
        bins even = {1'b0};
    }

    vs2_even: coverpoint ins.current.insn[20] {
        bins even = {1'b0};
    }

    vs2_vs1_no_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[19:16]) {
        bins overlapping = {1'b0};
    }

    cp_ssstrictv_vnarrow_overlapping_vd_vs2:  cross std_trap_vec, vtype_lmul_1, vs2_vd_overlap_lmul1, vd_even, vs2_even, vs2_vs1_no_overlap_lmul1;
