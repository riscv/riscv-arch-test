
    // All (EEW, LMUL, SEW) tuples where EMUL = (EEW/SEW)*LMUL is fractional (< 1)
    // width[14:12] encodes EEW: 000=8, 101=16, 110=32, 111=64
    vtype_lmul_sew_width_frac_emul : {coverpoint ins.current.insn[14:12],
                                       coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                       coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0]} {
        // EEW=8 (width=000): EMUL = (8/SEW)*LMUL
        bins eew8_sew16_lmul1  = {3'b000, 3'b000, 2'b01};  // EMUL = 1/2
        bins eew8_sew32_lmul1  = {3'b000, 3'b000, 2'b10};  // EMUL = 1/4
        bins eew8_sew32_lmul2  = {3'b000, 3'b001, 2'b10};  // EMUL = 1/2
        bins eew8_sew64_lmul1  = {3'b000, 3'b000, 2'b11};  // EMUL = 1/8
        bins eew8_sew64_lmul2  = {3'b000, 3'b001, 2'b11};  // EMUL = 1/4
        bins eew8_sew64_lmul4  = {3'b000, 3'b010, 2'b11};  // EMUL = 1/2
        // EEW=16 (width=101): EMUL = (16/SEW)*LMUL
        bins eew16_sew32_lmul1 = {3'b101, 3'b000, 2'b10};  // EMUL = 1/2
        bins eew16_sew64_lmul1 = {3'b101, 3'b000, 2'b11};  // EMUL = 1/4
        bins eew16_sew64_lmul2 = {3'b101, 3'b001, 2'b11};  // EMUL = 1/2
        // EEW=32 (width=110): EMUL = (32/SEW)*LMUL
        bins eew32_sew64_lmul1 = {3'b110, 3'b000, 2'b11};  // EMUL = 1/2
        // EEW=64: no fractional EMUL possible with integer LMUL
    }

    cp_ssstrictv_ls_fractional_emul: cross std_trap_vec, vtype_lmul_sew_width_frac_emul;
