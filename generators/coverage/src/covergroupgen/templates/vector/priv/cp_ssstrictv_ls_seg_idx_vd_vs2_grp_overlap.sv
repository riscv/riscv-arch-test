// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Indexed segment load dest groups (EMUL=2) cannot overlap vs2 index group.
    // Single bin matches every overlapping (vd, vs2, nf) tuple — each indexed
    // segment cg only fires its own nf, so per-tuple bins would leave most dead.
    vd_vs2_grp_overlap_lmul2 : coverpoint {ins.current.insn[11:7],
                                 ins.current.insn[24:20],
                                 ins.current.insn[31:29]} {
        bins seg_idx_grp_overlap = {{5'd8,  5'd8,  3'b001},  // NFIELDS=2 vs2=vd
                                    {5'd8,  5'd9,  3'b001},  // NFIELDS=2 vs2=vd+1
                                    {5'd8,  5'd10, 3'b001},  // NFIELDS=2 vs2=vd+2
                                    {5'd8,  5'd11, 3'b001},  // NFIELDS=2 vs2=vd+3
                                    {5'd8,  5'd12, 3'b010},  // NFIELDS=3 vs2=vd+4
                                    {5'd8,  5'd13, 3'b010},  // NFIELDS=3 vs2=vd+5
                                    {5'd8,  5'd14, 3'b011},  // NFIELDS=4 vs2=vd+6
                                    {5'd8,  5'd15, 3'b011}}; // NFIELDS=4 vs2=vd+7
    }

    cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap: cross std_trap_vec, vtype_sew_supported, vtype_lmul_2, vd_vs2_grp_overlap_lmul2;

//// end cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap /////////////////////////////////////////////////////////
