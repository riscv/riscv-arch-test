// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vadc_vsbc_vd_v0_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vadc (funct6=010000) or vsbc (funct6=010010) with vd=v0 (reserved).
    // Single bin matches either funct6 so this cp behaves identically across
    // vadc_v[ivx]m and vsbc_v[vx]m covergroups (each cg samples only its own
    // funct6 — separate per-opcode bins would leave the other always-0 dead).
    funct6_vadc_vsbc_e6d8ae: coverpoint ins.current.insn[31:26] {
        bins vadc_vsbc = {6'b010000, 6'b010010};
    }

    cp_ssstrictv_vadc_vsbc_vd_v0_reserved: cross std_trap_vec, funct6_vadc_vsbc_e6d8ae, vd_v0;

//// end cp_ssstrictv_vadc_vsbc_vd_v0_reserved /////////////////////////////////////////////////////////////
