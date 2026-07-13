// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrict_ls_nf_eew_emul8 — EMUL=8, NFIELDS>=2: EMUL*NFIELDS >= 16 > 8 (reserved, must trap)
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    emul_8_ls : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                 ins.current.insn[14:12]} {
        bins emul_eq_8 = {{3'b011, 2'b00, 3'b000},  // EEW=SEW LMUL=8 (8/8)
                          {3'b011, 2'b01, 3'b101},  //                (16/16)
                          {3'b011, 2'b10, 3'b110},  //                (32/32)
                          {3'b011, 2'b11, 3'b111},  //                (64/64)
                          {3'b010, 2'b00, 3'b101},  // EEW=2*SEW LMUL=4 (8→16)
                          {3'b010, 2'b01, 3'b110},  //                  (16→32)
                          {3'b010, 2'b10, 3'b111},  //                  (32→64)
                          {3'b001, 2'b00, 3'b110},  // EEW=4*SEW LMUL=2 (8→32)
                          {3'b001, 2'b01, 3'b111},  //                  (16→64)
                          {3'b000, 2'b00, 3'b111}}; // EEW=8*SEW LMUL=1 (8→64)
    }

    nf_ge2 : coverpoint ins.current.insn[31:29] {
        bins nf = {[1:7]};
    }

    cp_ssstrict_ls_nf_eew_emul8 : cross std_trap_vec, vtype_sew_supported, emul_8_ls, nf_ge2;

//// end cp_ssstrict_ls_nf_eew_emul8 ///////////////////////////////////////////////////////////////////////
