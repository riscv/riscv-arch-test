// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vmv8r_off_group
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vmv8r.v (simm=7): vd or vs2 must be divisible by 8
    simm_vmv8r_off: coverpoint ins.current.insn[19:15] {
        bins nreg8 = {5'b00111};
    }

    // Cross vmv8r.v with off-group vd or vs2 (not divisible by 8)
    cp_ssstrictv_vmv8r_vd_off_group : cross std_trap_vec, simm_vmv8r_off, vd_all_reg_unaligned_lmul_8;
    cp_ssstrictv_vmv8r_vs2_off_group : cross std_trap_vec, simm_vmv8r_off, vs2_all_reg_unaligned_lmul_8;

//// end cp_ssstrictv_vmv8r_off_group ///////////////////////////////////////////////////////////
