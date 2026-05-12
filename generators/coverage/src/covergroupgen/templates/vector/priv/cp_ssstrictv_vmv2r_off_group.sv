// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vmv2r_off_group
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vmv2r.v (simm=1): vd or vs2 must be divisible by 2
    simm_vmv2r_off: coverpoint ins.current.insn[19:15] {
        bins nreg2 = {5'b00001};
    }

    // Cross vmv2r.v with off-group vd or vs2 (not divisible by 2)
    cp_ssstrictv_vmv2r_vd_off_group : cross std_trap_vec, simm_vmv2r_off, vd_all_reg_unaligned_lmul_2;
    cp_ssstrictv_vmv2r_vs2_off_group : cross std_trap_vec, simm_vmv2r_off, vs2_all_reg_unaligned_lmul_2;

//// end cp_ssstrictv_vmv2r_off_group ///////////////////////////////////////////////////////////
