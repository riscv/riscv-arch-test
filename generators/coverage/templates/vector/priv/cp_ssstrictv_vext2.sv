    // Custom coverpoints for Vector zext and sext operations

    vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }

    vs2_even: coverpoint ins.current.insn[15] {
        bins odd = {1'b0};
    }

    vd_even: coverpoint ins.current.insn[7] {
        bins odd = {1'b0};
    }

    cp_ssstrictv_vext2_overlapping_vd_vs2:    cross std_trap_vec, vtype_lmul_2, vs2_vd_overlap_lmul2, vs2_even, vd_even;
