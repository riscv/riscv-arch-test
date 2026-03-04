    vs1_vd_overlap_lmul1: coverpoint (ins.current.insn[19:16] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }

    vs2_vd_no_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b0};
    }

    cp_exceptionsv_vd_vs1_overlap: cross std_trap_vec, vtype_lmul_1, vs1_vd_overlap_lmul1, vs1_all_reg_unaligned_lmul_2, vs2_vd_no_overlap_lmul1;
