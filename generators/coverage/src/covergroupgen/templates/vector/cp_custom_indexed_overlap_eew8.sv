    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_indexed_overlap_eew8
    //
    // Index EEW = 8. Coverage for legal vd/vs2 register-group overlap per
    // V-spec register overlap rules:
    //   (a) EEW_dest == EEW_src           -> any overlap legal
    //   (b) EEW_dest <  EEW_src           -> overlap in LOWEST part of source group
    //   (c) EEW_dest >  EEW_src, EMUL_src>=1 -> overlap in HIGHEST part of destination group
    // For indexed loads: dest = vd (EEW=SEW), src = vs2 (EEW=8).
    // Bins enumerate only vd values aligned to the minimum legal EMUL_dest.
    //////////////////////////////////////////////////////////////////////////////////

    `ifdef COVER_VLS8
        // SEW=8, EEW=8 -> rule (a): vd == vs2 legal. Any vd hittable.
        cp_custom_indexed_overlap_eew8_sew8 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
            (ins.current.vd == ins.current.vs2) & (ins.trap == 0)
        );
    `endif

    `ifdef COVER_VLS16
        // SEW=16, EEW=8 -> rule (c). LMUL >= 2 -> vd aligned to 2.
        cp_custom_indexed_overlap_eew8_sew16 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") < 4) &
            (ins.get_vr_reg(ins.current.vs2) > ins.get_vr_reg(ins.current.vd)) &
            (ins.get_vr_reg(ins.current.vs2) < ins.get_vr_reg(ins.current.vd) + (1 << get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"))) &
            (ins.trap == 0)
        ) {
            bins v0  = {v0};
            bins v2  = {v2};
            bins v4  = {v4};
            bins v6  = {v6};
            bins v8  = {v8};
            bins v10 = {v10};
            bins v12 = {v12};
            bins v14 = {v14};
            bins v16 = {v16};
            bins v18 = {v18};
            bins v20 = {v20};
            bins v22 = {v22};
            bins v24 = {v24};
            bins v26 = {v26};
            bins v28 = {v28};
            bins v30 = {v30};
        }
    `endif

    `ifdef COVER_VLS32
        // SEW=32, EEW=8 -> rule (c). LMUL >= 4 -> vd aligned to 4.
        cp_custom_indexed_overlap_eew8_sew32 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") < 4) &
            (ins.get_vr_reg(ins.current.vs2) > ins.get_vr_reg(ins.current.vd)) &
            (ins.get_vr_reg(ins.current.vs2) < ins.get_vr_reg(ins.current.vd) + (1 << get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"))) &
            (ins.trap == 0)
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
    `endif

    `ifdef COVER_VLS64
        // SEW=64, EEW=8 -> rule (c). LMUL = 8 -> vd aligned to 8, max v24.
        cp_custom_indexed_overlap_eew8_sew64 : coverpoint ins.get_vr_reg(ins.current.vd) iff (
            (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") < 4) &
            (ins.get_vr_reg(ins.current.vs2) > ins.get_vr_reg(ins.current.vd)) &
            (ins.get_vr_reg(ins.current.vs2) < ins.get_vr_reg(ins.current.vd) + (1 << get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul"))) &
            (ins.trap == 0)
        ) {
            bins v0  = {v0};
            bins v8  = {v8};
            bins v16 = {v16};
            bins v24 = {v24};
        }
    `endif

    //// end cp_custom_indexed_overlap_eew8////////////////////////////////////////////////
