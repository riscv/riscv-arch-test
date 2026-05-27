// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_seg_vd_overflow_emulgt1
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Segment load/store where vd + NFIELDS * LMUL > 32 with LMUL > 1.
    // Single bin matches every overflowing (lmul, nf, vd) tuple — each
    // segment cg only fires its own nf, so per-tuple bins would leave most
    // always dead.
    vd_nf_lmul_overflow : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                           ins.current.insn[31:29],
                           ins.current.insn[11:7]} {
        bins seg_lmul_overflow = {{3'b001, 3'b001, 5'd30},  // LMUL=2 nf=2 vd=30
                                  {3'b001, 3'b010, 5'd28},  // LMUL=2 nf=3 vd=28
                                  {3'b001, 3'b010, 5'd30},  // LMUL=2 nf=3 vd=30
                                  {3'b001, 3'b011, 5'd26},  // LMUL=2 nf=4 vd=26
                                  {3'b001, 3'b011, 5'd28},  // LMUL=2 nf=4 vd=28
                                  {3'b001, 3'b011, 5'd30},  // LMUL=2 nf=4 vd=30
                                  {3'b010, 3'b001, 5'd28}}; // LMUL=4 nf=2 vd=28
    }

    cp_ssstrictv_ls_seg_vd_overflow_emulgt1: cross std_trap_vec, vtype_sew_supported, vd_nf_lmul_overflow;

//// end cp_ssstrictv_ls_seg_vd_overflow_emulgt1 /////////////////////////////////////////////////////////
