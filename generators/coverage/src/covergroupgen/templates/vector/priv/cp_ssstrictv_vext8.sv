    // Custom coverpoints for Vector zext and sext operations

    vs2_vd_overlap_lmul8: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
        bins overlapping = {1'b1};
    }

    vs2_reg_not_top_lmul_8: coverpoint ins.current.insn[24:20] {
        wildcard bins range = {[5'b??000: 5'b??110]};
    }

    cp_ssstrictv_vext8_overlapping_vd_vs2:    cross std_trap_vec, vtype_lmul_8, vs2_vd_overlap_lmul8, vd_all_reg_aligned_lmul_8, vs2_reg_not_top_lmul_8;
