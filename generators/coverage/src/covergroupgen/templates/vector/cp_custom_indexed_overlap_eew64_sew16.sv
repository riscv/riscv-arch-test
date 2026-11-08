    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_indexed_overlap_eew64
    //
    // Index EEW = 64. Coverage for legal vd/vs2 register-group overlap per
    // V-spec register overlap rules:
    //   (a) EEW_dest == EEW_src           -> any overlap legal
    //   (b) EEW_dest <  EEW_src           -> overlap in LOWEST part of source group
    //   (c) EEW_dest >  EEW_src, EMUL_src>=1 -> overlap in HIGHEST part of destination group
    // For indexed loads: dest = vd (EEW=SEW), src = vs2 (EEW=64).
    // Bins enumerate only vd values aligned to the minimum legal EMUL_dest.
    //////////////////////////////////////////////////////////////////////////////////

    // SEW=16, EEW=64 -> rule (b). EMUL_src=4*LMUL, vd aligned to 4.
    cp_custom_indexed_overlap_eew64_sew16 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
        (ins.current.vd == ins.current.vs2) & (ins.trap == 0)
    ) {
        bins v0  = {v0};
        bins v4  = {v4};
        bins v8  = {v8};
        bins v12 = {v12};
        bins v16 = {v16};
        bins v20 = {v20};
        bins v24 = {v24};
        bins v28 = {v28};
    }

    //// end cp_custom_indexed_overlap_eew64////////////////////////////////////////////////
