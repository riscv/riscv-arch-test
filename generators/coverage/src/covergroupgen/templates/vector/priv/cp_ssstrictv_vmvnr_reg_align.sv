// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vmvnr_reg_align
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vmv2r.v (simm=1): both vd and vs2 must be divisible by 2
    simm_vmv2r: coverpoint ins.current.insn[19:15] {
        bins nreg2 = {5'b00001};
    }

    // vmv4r.v (simm=3): both vd and vs2 must be divisible by 4
    simm_vmv4r: coverpoint ins.current.insn[19:15] {
        bins nreg4 = {5'b00011};
    }

    // vmv8r.v (simm=7): both vd and vs2 must be divisible by 8
    simm_vmv8r: coverpoint ins.current.insn[19:15] {
        bins nreg8 = {5'b00111};
    }

    // Both vd and vs2 unaligned for vmv2r.v
    cp_ssstrictv_vmv2r_both_unaligned: cross std_trap_vec, simm_vmv2r, vd_all_reg_unaligned_lmul_2, vs2_all_reg_unaligned_lmul_2;

    // Both vd and vs2 unaligned for vmv4r.v
    cp_ssstrictv_vmv4r_both_unaligned: cross std_trap_vec, simm_vmv4r, vd_all_reg_unaligned_lmul_4, vs2_all_reg_unaligned_lmul_4;

    // Both vd and vs2 unaligned for vmv8r.v
    cp_ssstrictv_vmv8r_both_unaligned: cross std_trap_vec, simm_vmv8r, vd_all_reg_unaligned_lmul_8, vs2_all_reg_unaligned_lmul_8;

//// end cp_ssstrictv_vmvnr_reg_align /////////////////////////////////////////////////////////////
