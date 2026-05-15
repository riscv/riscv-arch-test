    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_inactive_not_set
    // Verifies that inactive elements do not set FP flags.
    // Uses vl=1, unmasked, v0[0]=0 (element 1 inactive), vs2=zero (flag-setting
    // input for vfrsqrt7 DZ), and fflags pre-cleared. If the inactive element
    // incorrectly raises flags, fflags will be non-zero after execution.
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    mask_enabled: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b0};
    }

    vfp_flags_fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") {
        bins clear = {0};
    }

    // Check element 0 of vs2 is zero. We check [15:0] which is the smallest
    // FP SEW (16). For SEW32/64, zero means all bits are 0 including [15:0].
    // For non-zero FP values, [15:0] is always nonzero (exponent/mantissa bits).
    vfsqrt_flag_set : coverpoint (ins.current.vs2_val[15:0] == 0) {
        bins target = {1};
    }

    vl_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        //Any value between max and 1
        bins target = {1};
    }

    v0_element_1_active : coverpoint (ins.current.v0_val[0]) {
        bins target = {0};
    }

    cp_custom_vfp_flags_inactive_not_set : cross std_vec, vl_one, mask_enabled, v0_element_1_active, vfsqrt_flag_set, vfp_flags_fp_flags_clear;
`else
    `ifdef FLEN64
    mask_enabled: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b0};
    }

    vfp_flags_fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") {
        bins clear = {0};
    }

    vfsqrt_flag_set : coverpoint (ins.current.vs2_val[15:0] == 0) {
        bins target = {1};
    }

    vl_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins target = {1};
    }

    v0_element_1_active : coverpoint (ins.current.v0_val[0]) {
        bins target = {0};
    }

    cp_custom_vfp_flags_inactive_not_set : cross std_vec, vl_one, mask_enabled, v0_element_1_active, vfsqrt_flag_set, vfp_flags_fp_flags_clear;
    `endif
`endif

    //// end cp_custom_vfp_flags_inactive_not_set////////////////////////////////////////////////
