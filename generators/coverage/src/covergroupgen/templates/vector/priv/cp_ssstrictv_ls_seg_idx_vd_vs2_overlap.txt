// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_seg_idx_vd_vs2_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Verify indexed segment load destination groups cannot overlap vs2 source index register
    vd_vs2_nf_overlap : {coverpoint ins.current.insn[11:7],
                         coverpoint ins.current.insn[24:20],
                         coverpoint ins.current.insn[31:29]} {
        bins nf1_vd8_vs2eq8   = {5'd8,  5'd8,  3'b001};  // NFIELDS=2, vs2=vd (1st dest group)
        bins nf1_vd8_vs2eq9   = {5'd8,  5'd9,  3'b001};  // NFIELDS=2, vs2=vd+1 (2nd dest group)
        bins nf2_vd8_vs2eq10  = {5'd8,  5'd10, 3'b010};  // NFIELDS=3, vs2=vd+2 (3rd dest group)
        bins nf3_vd8_vs2eq11  = {5'd8,  5'd11, 3'b011};  // NFIELDS=4, vs2=vd+3 (4th dest group)
        bins nf4_vd8_vs2eq12  = {5'd8,  5'd12, 3'b100};  // NFIELDS=5, vs2=vd+4 (5th dest group)
        bins nf5_vd8_vs2eq13  = {5'd8,  5'd13, 3'b101};  // NFIELDS=6, vs2=vd+5 (6th dest group)
        bins nf6_vd8_vs2eq14  = {5'd8,  5'd14, 3'b110};  // NFIELDS=7, vs2=vd+6 (7th dest group)
        bins nf7_vd8_vs2eq15  = {5'd8,  5'd15, 3'b111};  // NFIELDS=8, vs2=vd+7 (8th dest group)
    }

    cp_ssstrictv_ls_seg_idx_vd_vs2_overlap: cross std_trap_vec, vtype_sew_supported, vtype_lmul_1, vd_vs2_nf_overlap;

//// end cp_ssstrictv_ls_seg_idx_vd_vs2_overlap ///////////////////////////////////////////////////////////
