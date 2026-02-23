    // Custom coverpoints for Vector widdening operations that end in .v*

    vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }

    vs2_vd_no_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b0};
    }

    cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1:          cross std_trap_vec, vtype_lmul_1, vs2_vd_overlap_lmul1, vs2_reg_aligned_lmul_2, vd_reg_aligned_lmul_2, vs1_vd_no_overlap_lmul1;
    cp_ssstrictv_vwiden_overlapping_vd_vs1_lmul1:          cross std_trap_vec, vtype_lmul_1, vs1_vd_overlap_lmul1, vs1_all_reg_aligned_lmul_2, vd_reg_aligned_lmul_2, vs2_vd_no_overlap_lmul1;
