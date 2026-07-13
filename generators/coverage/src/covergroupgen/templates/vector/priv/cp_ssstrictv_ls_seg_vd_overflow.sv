// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_seg_vd_overflow
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Segment load/store where vd + NFIELDS > 32 (register numbers past 31).
    // Single bin matches every (vd, nf) overflow tuple — each segment cg only
    // fires its own nf, so per-nf bins would leave 6/7 always dead.
    vd_nf_overflow : coverpoint {ins.current.insn[11:7],
                      ins.current.insn[31:29]} {
        bins seg_overflow = {{5'd31, 3'b001},  // NFIELDS=2, vd=31
                             {5'd30, 3'b010},  // NFIELDS=3, vd=30
                             {5'd29, 3'b011},  // NFIELDS=4, vd=29
                             {5'd28, 3'b100},  // NFIELDS=5, vd=28
                             {5'd27, 3'b101},  // NFIELDS=6, vd=27
                             {5'd26, 3'b110},  // NFIELDS=7, vd=26
                             {5'd25, 3'b111}}; // NFIELDS=8, vd=25
    }

    cp_ssstrictv_ls_seg_vd_overflow: cross std_trap_vec, vtype_sew_supported, vtype_lmul_1, vd_nf_overflow;

//// end cp_ssstrictv_ls_seg_vd_overflow ///////////////////////////////////////////////////////////
