    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ffLS_update_vl
    //////////////////////////////////////////////////////////////////////////////////

    // Fault-only-first load setup: LMUL=2, vl=VLMAX, masked with v0=1

    v0_eq_1: coverpoint unsigned'(ins.current.v0_val) {
        bins one = {1};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b0};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                        == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }

    cp_custom_ffLS_update_vl : cross std_vec, vtype_lmul_2, vl_max, mask_enabled, v0_eq_1;

    //// end cp_custom_ffLS_update_vl////////////////////////////////////////////////
