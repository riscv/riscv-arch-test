    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_indexed_overlap_eew8
    //
    // Index EEW = 8. Coverage for legal vd/vs2 register-group overlap per
    // V-spec register overlap rules:
    //   (a) EEW_dest == EEW_src           -> any overlap legal
    //   (b) EEW_dest <  EEW_src           -> overlap in LOWEST part of source group
    //   (c) EEW_dest >  EEW_src, EMUL_src>=1 -> overlap in HIGHEST part of destination group
    // For indexed loads: dest = vd (EEW=SEW), src = vs2 (EEW=8).
    //////////////////////////////////////////////////////////////////////////////////

    `ifdef COVER_VLS8
        // SEW=8, EEW=8 -> rule (a): vd == vs2 legal.
        cp_custom_indexed_overlap_eew8_sew8 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
            (ins.current.vd == ins.current.vs2) & (ins.trap == 0)
        );
    `endif

    `ifdef COVER_VLS16
        // SEW=16, EEW=8 -> rule (c): vs2 sits in upper part of vd group
        // (vd < vs2 < vd + LMUL). LMUL must be >= 2 for EMUL_src >= 1.
        cp_custom_indexed_overlap_eew8_sew16 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") < 4) &
            (ins.get_vr_reg(ins.current.vs2) > ins.get_vr_reg(ins.current.vd)) &
            (ins.get_vr_reg(ins.current.vs2) < ins.get_vr_reg(ins.current.vd) + (1 << get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"))) &
            (ins.trap == 0)
        );
    `endif

    `ifdef COVER_VLS32
        // SEW=32, EEW=8 -> rule (c). LMUL must be >= 4 for EMUL_src >= 1.
        cp_custom_indexed_overlap_eew8_sew32 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") < 4) &
            (ins.get_vr_reg(ins.current.vs2) > ins.get_vr_reg(ins.current.vd)) &
            (ins.get_vr_reg(ins.current.vs2) < ins.get_vr_reg(ins.current.vd) + (1 << get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"))) &
            (ins.trap == 0)
        );
    `endif

    `ifdef COVER_VLS64
        // SEW=64, EEW=8 -> rule (c). LMUL must be 8 for EMUL_src >= 1.
        cp_custom_indexed_overlap_eew8_sew64 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") < 4) &
            (ins.get_vr_reg(ins.current.vs2) > ins.get_vr_reg(ins.current.vd)) &
            (ins.get_vr_reg(ins.current.vs2) < ins.get_vr_reg(ins.current.vd) + (1 << get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"))) &
            (ins.trap == 0)
        );
    `endif

    //// end cp_custom_indexed_overlap_eew8////////////////////////////////////////////////
