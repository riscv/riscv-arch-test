// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Indexed segment load dest groups (EMUL=2) cannot overlap vs2 index group
    vd_vs2_grp_overlap_lmul2 : {coverpoint ins.current.insn[11:7],
                                 coverpoint ins.current.insn[24:20],
                                 coverpoint ins.current.insn[31:29]} {
        // LMUL=2, NFIELDS=2: dest groups [vd,vd+1] and [vd+2,vd+3], vs2 group [vs2,vs2+1]
        // vs2 group overlaps 1st dest group (vs2=vd)
        bins nf1_vd8_vs2eq8    = {5'd8,  5'd8,  3'b001};
        // vs2 group overlaps 1st dest group (vs2=vd+1, vs2 base inside 1st group)
        bins nf1_vd8_vs2eq9    = {5'd8,  5'd9,  3'b001};
        // vs2 group overlaps 2nd dest group (vs2=vd+2)
        bins nf1_vd8_vs2eq10   = {5'd8,  5'd10, 3'b001};
        // vs2 group overlaps 2nd dest group (vs2=vd+3, vs2 base inside 2nd group)
        bins nf1_vd8_vs2eq11   = {5'd8,  5'd11, 3'b001};
        // LMUL=2, NFIELDS=3: dest groups [8,9],[10,11],[12,13], vs2 overlaps 3rd group
        bins nf2_vd8_vs2eq12   = {5'd8,  5'd12, 3'b010};
        bins nf2_vd8_vs2eq13   = {5'd8,  5'd13, 3'b010};
        // LMUL=2, NFIELDS=4: dest groups [8,9],[10,11],[12,13],[14,15], vs2 overlaps 4th group
        bins nf3_vd8_vs2eq14   = {5'd8,  5'd14, 3'b011};
        bins nf3_vd8_vs2eq15   = {5'd8,  5'd15, 3'b011};
    }

    cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap: cross std_trap_vec, vtype_sew_supported, vtype_lmul_2, vd_vs2_grp_overlap_lmul2;

//// end cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap /////////////////////////////////////////////////////////
