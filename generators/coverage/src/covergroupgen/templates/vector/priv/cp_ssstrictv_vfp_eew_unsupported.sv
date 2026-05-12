// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vfp_eew_unsupported
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Vector FP operand EEW (=SEW) not a supported FP type width (includes FLEN < SEW)

    sew_unsupported_fp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        // SEW=8 (vsew=0) is never a supported FP width
        bins sew8 = {0};
        `ifndef D_COVERAGE
        // SEW=64 (vsew=3) unsupported without D extension (FLEN < 64)
        bins sew64 = {3};
        `endif
    }


    cp_ssstrictv_vfp_eew_unsupported: cross std_trap_vec, sew_unsupported_fp;

    // Edge case: still reserved when vl=0
    vl_zero_196c2e: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins zero = {0};
    }

    mstatus_vs_active_196c2e: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active = {[1:3]};
    }

    cp_ssstrictv_vfp_eew_unsupported_vl0: cross vtype_prev_vill_clear, vl_zero_196c2e, mstatus_vs_active_196c2e, sew_unsupported_fp;

    // Edge case: still reserved when vstart >= vl
    vstart_ge_vl_196c2e: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")) {
        bins true = {1'b1};
    }

    cp_ssstrictv_vfp_eew_unsupported_vstart_ge_vl: cross vtype_prev_vill_clear, vl_nonzero, mstatus_vs_active_196c2e, vstart_ge_vl_196c2e, sew_unsupported_fp;

//// end cp_ssstrictv_vfp_eew_unsupported ///////////////////////////////////////////////////////////
