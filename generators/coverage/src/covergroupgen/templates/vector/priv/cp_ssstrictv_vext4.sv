    // Custom coverpoints for Vector zext and sext operations

    vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
        bins overlapping = {1'b1};
    }

    vs2_reg_not_top_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard bins range = {[5'b???00: 5'b???10]};
    }

    cp_ssstrictv_vext4_overlapping_vd_vs2:    cross std_trap_vec, vtype_lmul_4, vs2_vd_overlap_lmul4, vd_reg_aligned_lmul_4, vs2_reg_not_top_lmul_4;
