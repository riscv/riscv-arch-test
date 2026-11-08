    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_indexed_overlap_eew32
    //
    // Index EEW = 32. Coverage for legal vd/vs2 register-group overlap per
    // V-spec register overlap rules:
    //   (a) EEW_dest == EEW_src           -> any overlap legal
    //   (b) EEW_dest <  EEW_src           -> overlap in LOWEST part of source group
    //   (c) EEW_dest >  EEW_src, EMUL_src>=1 -> overlap in HIGHEST part of destination group
    // For indexed loads: dest = vd (EEW=SEW), src = vs2 (EEW=32).
    // Bins enumerate only vd values aligned to the minimum legal EMUL_dest.
    //////////////////////////////////////////////////////////////////////////////////

    // SEW=32, EEW=32 -> rule (a): any vd legal.
    cp_custom_indexed_overlap_eew32_sew32 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
        (ins.current.vd == ins.current.vs2) & (ins.trap == 0)
    );

    //// end cp_custom_indexed_overlap_eew32////////////////////////////////////////////////
