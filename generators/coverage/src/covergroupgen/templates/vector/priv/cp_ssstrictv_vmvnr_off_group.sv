// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vmvnr_off_group
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vmv2r.v (simm=1): vd or vs2 must be divisible by 2
    simm_vmv2r: coverpoint ins.current.insn[19:15] {
        bins nreg2 = {5'b00001};
    }

    // vmv4r.v (simm=3): vd or vs2 must be divisible by 4
    simm_vmv4r: coverpoint ins.current.insn[19:15] {
        bins nreg4 = {5'b00011};
    }

    // vmv8r.v (simm=7): vd or vs2 must be divisible by 8
    simm_vmv8r: coverpoint ins.current.insn[19:15] {
        bins nreg8 = {5'b00111};
    }

    // Cross vmv2r.v with off-group vd or vs2 (not divisible by 2)
    cp_ssstrictv_vmv2r_vd_off_group : cross std_trap_vec, simm_vmv2r, vd_all_reg_unaligned_lmul_2;
    cp_ssstrictv_vmv2r_vs2_off_group : cross std_trap_vec, simm_vmv2r, vs2_all_reg_unaligned_lmul_2;

    // Cross vmv4r.v with off-group vd or vs2 (not divisible by 4)
    cp_ssstrictv_vmv4r_vd_off_group : cross std_trap_vec, simm_vmv4r, vd_all_reg_unaligned_lmul_4;
    cp_ssstrictv_vmv4r_vs2_off_group : cross std_trap_vec, simm_vmv4r, vs2_all_reg_unaligned_lmul_4;

    // Cross vmv8r.v with off-group vd or vs2 (not divisible by 8)
    cp_ssstrictv_vmv8r_vd_off_group : cross std_trap_vec, simm_vmv8r, vd_all_reg_unaligned_lmul_8;
    cp_ssstrictv_vmv8r_vs2_off_group : cross std_trap_vec, simm_vmv8r, vs2_all_reg_unaligned_lmul_8;

//// end cp_ssstrictv_vmvnr_off_group ///////////////////////////////////////////////////////////
