// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_seg_idx_vd_vs2_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Verify indexed segment load destination groups cannot overlap vs2 index register.
    // Single bin matches every (vd, vs2, nf) overlap tuple — each indexed segment cg
    // only fires its own nf, so per-nf bins would leave most always dead.
    vd_vs2_nf_overlap : coverpoint {ins.current.insn[11:7],
                         ins.current.insn[24:20],
                         ins.current.insn[31:29]} {
        bins seg_idx_overlap = {{5'd8,  5'd8,  3'b001},  // NFIELDS=2, vs2=vd
                                {5'd8,  5'd9,  3'b001},  // NFIELDS=2, vs2=vd+1
                                {5'd8,  5'd10, 3'b010},  // NFIELDS=3, vs2=vd+2
                                {5'd8,  5'd11, 3'b011},  // NFIELDS=4, vs2=vd+3
                                {5'd8,  5'd12, 3'b100},  // NFIELDS=5, vs2=vd+4
                                {5'd8,  5'd13, 3'b101},  // NFIELDS=6, vs2=vd+5
                                {5'd8,  5'd14, 3'b110},  // NFIELDS=7, vs2=vd+6
                                {5'd8,  5'd15, 3'b111}}; // NFIELDS=8, vs2=vd+7
    }

    cp_ssstrictv_ls_seg_idx_vd_vs2_overlap: cross std_trap_vec, vtype_sew_supported, vtype_lmul_1, vd_vs2_nf_overlap;

//// end cp_ssstrictv_ls_seg_idx_vd_vs2_overlap ///////////////////////////////////////////////////////////
