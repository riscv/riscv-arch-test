
    // EMUL = 1/16 for vle8/vse8: (8/SEW) * LMUL combinations that produce 1/16
    vtype_lmul_sew_emulf16 : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                               coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0]} {
        bins lmulf8_sew16 = {3'b101, 2'b01};  // LMUL=1/8, SEW=16: EMUL = (8/16)*(1/8) = 1/16
        bins lmulf4_sew32 = {3'b110, 2'b10};  // LMUL=1/4, SEW=32: EMUL = (8/32)*(1/4) = 1/16
        bins lmulf2_sew64 = {3'b111, 2'b11};  // LMUL=1/2, SEW=64: EMUL = (8/64)*(1/2) = 1/16
    }

    cp_ssstrictv_ls_emul_f16: cross std_trap_vec, vtype_lmul_sew_emulf16;
