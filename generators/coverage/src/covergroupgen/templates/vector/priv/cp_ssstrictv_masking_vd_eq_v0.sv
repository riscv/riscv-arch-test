
    vd_eq_v0 : coverpoint ins.current.insn[11:7] {
      bins v0 = { 5'b00000 };
    }

    cp_ssstrictv_masking_vd_eq_v0 : cross std_trap_vec, vtype_lmul_1, vd_eq_v0, vd_ne_vs1, vd_ne_vs2, vs2_ne_vs1, mask_enabled;
