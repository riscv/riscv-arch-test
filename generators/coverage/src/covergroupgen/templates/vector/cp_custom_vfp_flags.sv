    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_fflags_vdoun : coverpoint {
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0],
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        // Value of FCSR.fflags
        wildcard bins NV   = {10'b0????_1????};
        wildcard bins NV1  = {10'b1????_1????};
        wildcard bins DZ   = {10'b?0???_?1???};
        wildcard bins DZ1  = {10'b?1???_?1???};
        wildcard bins OF   = {10'b??0??_??1??};
        wildcard bins OF1  = {10'b??1??_??1??};
        wildcard bins UF   = {10'b???0?_???1?};
        wildcard bins UF1  = {10'b???1?_???1?};
        wildcard bins NX   = {10'b????0_????1};
        wildcard bins NX1  = {10'b????1_????1};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b0};
    }

    vfp_flags_fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0] {
        bins clear = {0};
    }

    vfsqrt_flag_set : coverpoint (ins.current.insn == "vfrsqrt7.v" & ins.current.vs2_val == 0) {
        bins target = {1};
    }

    vl_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        //Any value between max and 1
        bins target = {1};
    }

    v0_element_1_active : coverpoint (ins.current.v0_val[0]) {
        bins target = {1};
    }

    cp_custom_vfp_flags_set : cross std_vec, cp_csr_fflags_vdoun;

    cp_custom_vfp_flags_inactive_not_set : cross std_vec, vl_one, mask_enabled, v0_element_1_active, vfsqrt_flag_set, vfp_flags_fp_flags_clear;

    //// end cp_custom_vfp_flags////////////////////////////////////////////////
