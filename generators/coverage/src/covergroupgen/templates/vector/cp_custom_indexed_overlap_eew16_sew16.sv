    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_indexed_overlap_eew16
    //
    // Index EEW = 16. Coverage for legal vd/vs2 register-group overlap per
    // V-spec register overlap rules:
    //   (a) EEW_dest == EEW_src           -> any overlap legal
    //   (b) EEW_dest <  EEW_src           -> overlap in LOWEST part of source group
    //   (c) EEW_dest >  EEW_src, EMUL_src>=1 -> overlap in HIGHEST part of destination group
    // For indexed loads: dest = vd (EEW=SEW), src = vs2 (EEW=16).
    // Bins enumerate only vd values aligned to the minimum legal EMUL_dest.
    //////////////////////////////////////////////////////////////////////////////////

    // SEW=16, EEW=16 -> rule (a): any vd legal.
    cp_custom_indexed_overlap_eew16_sew16 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
        (ins.current.vd == ins.current.vs2) & (ins.trap == 0)
    );

    //// end cp_custom_indexed_overlap_eew16////////////////////////////////////////////////
