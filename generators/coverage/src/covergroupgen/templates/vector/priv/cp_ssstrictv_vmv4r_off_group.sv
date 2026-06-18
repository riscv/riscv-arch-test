// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vmv4r_off_group
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vmv4r.v (simm=3): vd or vs2 must be divisible by 4
    simm_vmv4r_off: coverpoint ins.current.insn[19:15] {
        bins nreg4 = {5'b00011};
    }

    // Cross vmv4r.v with off-group vd or vs2 (not divisible by 4)
    cp_ssstrictv_vmv4r_vd_off_group : cross std_trap_vec, simm_vmv4r_off, vd_all_reg_unaligned_lmul_4;
    cp_ssstrictv_vmv4r_vs2_off_group : cross std_trap_vec, simm_vmv4r_off, vs2_all_reg_unaligned_lmul_4;

//// end cp_ssstrictv_vmv4r_off_group ///////////////////////////////////////////////////////////
