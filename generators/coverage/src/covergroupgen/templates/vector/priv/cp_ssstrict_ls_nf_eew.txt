// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrict_ls_nf_eew
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // EMUL = (EEW/SEW) * LMUL = 8 from (vlmul, vsew, width) tuples
    emul_8_ls : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                 coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                 coverpoint ins.current.insn[14:12]} {
        // EEW=SEW, LMUL=8
        bins m8_sew8_eew8     = {3'b011, 2'b00, 3'b000};
        bins m8_sew16_eew16   = {3'b011, 2'b01, 3'b101};
        bins m8_sew32_eew32   = {3'b011, 2'b10, 3'b110};
        bins m8_sew64_eew64   = {3'b011, 2'b11, 3'b111};
        // EEW=2*SEW, LMUL=4
        bins m4_sew8_eew16    = {3'b010, 2'b00, 3'b101};
        bins m4_sew16_eew32   = {3'b010, 2'b01, 3'b110};
        bins m4_sew32_eew64   = {3'b010, 2'b10, 3'b111};
        // EEW=4*SEW, LMUL=2
        bins m2_sew8_eew32    = {3'b001, 2'b00, 3'b110};
        bins m2_sew16_eew64   = {3'b001, 2'b01, 3'b111};
        // EEW=8*SEW, LMUL=1
        bins m1_sew8_eew64    = {3'b000, 2'b00, 3'b111};
    }

    // NFIELDS >= 2 (nf field = NFIELDS-1 >= 1)
    nf_ge2 : coverpoint ins.current.insn[31:29] {
        bins nf[] = {[1:7]};
    }

    // EMUL=8, NFIELDS>=2: EMUL*NFIELDS >= 16 > 8 (reserved, must trap)
    cp_ssstrict_ls_nf_eew_emul8 : cross std_trap_vec, vtype_sew_supported, emul_8_ls, nf_ge2;

    // EMUL = (EEW/SEW) * LMUL = 4 from (vlmul, vsew, width) tuples
    emul_4_ls : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                 coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                 coverpoint ins.current.insn[14:12]} {
        // EEW=SEW, LMUL=4
        bins m4_sew8_eew8     = {3'b010, 2'b00, 3'b000};
        bins m4_sew16_eew16   = {3'b010, 2'b01, 3'b101};
        bins m4_sew32_eew32   = {3'b010, 2'b10, 3'b110};
        bins m4_sew64_eew64   = {3'b010, 2'b11, 3'b111};
        // EEW=2*SEW, LMUL=2
        bins m2_sew8_eew16    = {3'b001, 2'b00, 3'b101};
        bins m2_sew16_eew32   = {3'b001, 2'b01, 3'b110};
        bins m2_sew32_eew64   = {3'b001, 2'b10, 3'b111};
        // EEW=4*SEW, LMUL=1
        bins m1_sew8_eew32    = {3'b000, 2'b00, 3'b110};
        bins m1_sew16_eew64   = {3'b000, 2'b01, 3'b111};
        // EEW=8*SEW, LMUL=mf2
        bins mf2_sew8_eew64   = {3'b111, 2'b00, 3'b111};
    }

    // NFIELDS >= 3 (nf field = NFIELDS-1 >= 2)
    nf_ge3 : coverpoint ins.current.insn[31:29] {
        bins nf[] = {[2:7]};
    }

    // EMUL=4, NFIELDS>=3: EMUL*NFIELDS >= 12 > 8 (reserved, must trap)
    cp_ssstrict_ls_nf_eew_emul4 : cross std_trap_vec, vtype_sew_supported, emul_4_ls, nf_ge3;

    // EMUL = (EEW/SEW) * LMUL = 2 from (vlmul, vsew, width) tuples
    emul_2_ls : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                 coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                 coverpoint ins.current.insn[14:12]} {
        // EEW=SEW, LMUL=2
        bins m2_sew8_eew8     = {3'b001, 2'b00, 3'b000};
        bins m2_sew16_eew16   = {3'b001, 2'b01, 3'b101};
        bins m2_sew32_eew32   = {3'b001, 2'b10, 3'b110};
        bins m2_sew64_eew64   = {3'b001, 2'b11, 3'b111};
        // EEW=2*SEW, LMUL=1
        bins m1_sew8_eew16    = {3'b000, 2'b00, 3'b101};
        bins m1_sew16_eew32   = {3'b000, 2'b01, 3'b110};
        bins m1_sew32_eew64   = {3'b000, 2'b10, 3'b111};
        // EEW=4*SEW, LMUL=mf2
        bins mf2_sew8_eew32   = {3'b111, 2'b00, 3'b110};
        bins mf2_sew16_eew64  = {3'b111, 2'b01, 3'b111};
        // EEW=8*SEW, LMUL=mf4
        bins mf4_sew8_eew64   = {3'b110, 2'b00, 3'b111};
    }

    // NFIELDS >= 5 (nf field = NFIELDS-1 >= 4)
    nf_ge5 : coverpoint ins.current.insn[31:29] {
        bins nf[] = {[4:7]};
    }

    // EMUL=2, NFIELDS>=5: EMUL*NFIELDS >= 10 > 8 (reserved, must trap)
    cp_ssstrict_ls_nf_eew_emul2 : cross std_trap_vec, vtype_sew_supported, emul_2_ls, nf_ge5;

//// end cp_ssstrict_ls_nf_eew //////////////////////////////////////////////////////////////////////////
