
    // EMUL = 16 for load/store: (EEW/SEW) * LMUL = 16 combinations across all EEWs
    vtype_lmul_sew_emul16 : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                              coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0]} {
        bins lmul8_sew8  = {3'b011, 2'b00};  // LMUL=8, SEW=8:  EEW=16 -> EMUL=16
        bins lmul4_sew8  = {3'b010, 2'b00};  // LMUL=4, SEW=8:  EEW=32 -> EMUL=16
        bins lmul8_sew16 = {3'b011, 2'b01};  // LMUL=8, SEW=16: EEW=32 -> EMUL=16
        bins lmul2_sew8  = {3'b001, 2'b00};  // LMUL=2, SEW=8:  EEW=64 -> EMUL=16
        bins lmul4_sew16 = {3'b010, 2'b01};  // LMUL=4, SEW=16: EEW=64 -> EMUL=16
        bins lmul8_sew32 = {3'b011, 2'b10};  // LMUL=8, SEW=32: EEW=64 -> EMUL=16
    }

    cp_ssstrictv_ls_emul_16: cross std_trap_vec, vtype_lmul_sew_emul16;
