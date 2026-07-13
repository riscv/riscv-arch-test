// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vfp_widen_eew_unsupported
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Widening/narrowing FP: wider operand EEW=2*SEW not a supported FP width

    sew_widen_unsupported_fp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        `ifndef D_COVERAGE
        // SEW=32 (vsew=2) widens to EEW=64, unsupported without D extension
        bins sew32 = {2};
        `endif
    }


    cp_ssstrictv_vfp_widen_eew_unsupported: cross std_trap_vec, sew_widen_unsupported_fp;

    // Edge case: still reserved when vl=0
    vl_zero_155ca2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins zero = {0};
    }

    mstatus_vs_active_155ca2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active = {[1:3]};
    }

    cp_ssstrictv_vfp_widen_eew_unsupported_vl0: cross vtype_prev_vill_clear, vl_zero_155ca2, mstatus_vs_active_155ca2, sew_widen_unsupported_fp;

    // Edge case: still reserved when vstart >= vl
    vstart_ge_vl_155ca2: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")) {
        bins true = {1'b1};
    }

    cp_ssstrictv_vfp_widen_eew_unsupported_vstart_ge_vl: cross vtype_prev_vill_clear, vl_nonzero, mstatus_vs_active_155ca2, vstart_ge_vl_155ca2, sew_widen_unsupported_fp;

//// end cp_ssstrictv_vfp_widen_eew_unsupported ///////////////////////////////////////////////////////////
