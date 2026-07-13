// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrict_ls_nf_eew_emul2 — EMUL=2, NFIELDS>=5: EMUL*NFIELDS >= 10 > 8 (reserved, must trap)
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    emul_2_ls : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                 ins.current.insn[14:12]} {
        bins emul_eq_2 = {{3'b001, 2'b00, 3'b000},  // EEW=SEW LMUL=2 (8/8)
                          {3'b001, 2'b01, 3'b101},  //                (16/16)
                          {3'b001, 2'b10, 3'b110},  //                (32/32)
                          {3'b001, 2'b11, 3'b111},  //                (64/64)
                          {3'b000, 2'b00, 3'b101},  // EEW=2*SEW LMUL=1 (8→16)
                          {3'b000, 2'b01, 3'b110},  //                  (16→32)
                          {3'b000, 2'b10, 3'b111},  //                  (32→64)
                          {3'b111, 2'b00, 3'b110},  // EEW=4*SEW LMUL=mf2 (8→32)
                          {3'b111, 2'b01, 3'b111},  //                    (16→64)
                          {3'b110, 2'b00, 3'b111}}; // EEW=8*SEW LMUL=mf4 (8→64)
    }

    nf_ge5 : coverpoint ins.current.insn[31:29] {
        bins nf = {[4:7]};
    }

    cp_ssstrict_ls_nf_eew_emul2 : cross std_trap_vec, vtype_sew_supported, emul_2_ls, nf_ge5;

//// end cp_ssstrict_ls_nf_eew_emul2 ///////////////////////////////////////////////////////////////////////
