// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_emul_nfields_16
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // EMUL * NFIELDS = 16 (reserved) for segment loads/stores where EEW = SEW (EMUL = LMUL).
    // Single bin matches any of the 3 reserved (lmul, nf) tuples — each segment cg only
    // exercises one nf value so per-tuple bins leave the others permanently dead.
    vtype_lmul_nf_emul_nfields_16 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                     ins.current.insn[31:29]} {
        bins emul_nf_eq_16 = {{3'b011, 3'b001},   // LMUL=8 NFIELDS=2
                              {3'b010, 3'b011},   // LMUL=4 NFIELDS=4
                              {3'b001, 3'b111}};  // LMUL=2 NFIELDS=8
    }

    cp_ssstrictv_ls_emul_nfields_16: cross std_trap_vec, vtype_sew_supported, vtype_lmul_nf_emul_nfields_16;

//// end cp_ssstrictv_ls_emul_nfields_16 ///////////////////////////////////////////////////////////
