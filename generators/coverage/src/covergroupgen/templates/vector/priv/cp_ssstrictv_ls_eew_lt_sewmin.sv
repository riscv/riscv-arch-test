// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_eew_lt_sewmin
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Vector load/store EEW (from width field) smaller than SEWMIN is reserved.
    // The whole family only exists when SEWMIN > 8 (i.e. SEW8 isn't supported);
    // otherwise none of the encodable widths (EEW=8/16/32) are reserved and
    // these coverpoints have nothing to exercise. Wrap in `ifndef SEW8_SUPPORTED`
    // so the coverpoints + crosses are entirely absent on configurations where
    // every relevant SEW is supported (e.g. sail/spike/whisper *-max).
    `ifndef SEW8_SUPPORTED
    ls_eew_below_sewmin: coverpoint ins.current.insn[14:12] {
        bins eew8  = {3'b000};  // width=000 -> EEW=8, reserved if SEWMIN > 8
        `ifndef SEW16_SUPPORTED
        bins eew16 = {3'b101};  // width=101 -> EEW=16, reserved if SEWMIN > 16
        `endif
        `ifndef SEW32_SUPPORTED
        bins eew32 = {3'b110};  // width=110 -> EEW=32, reserved if SEWMIN > 32
        `endif
    }


    cp_ssstrictv_ls_eew_lt_sewmin: cross std_trap_vec, ls_eew_below_sewmin;

    // Edge case: still reserved when vl=0
    vl_zero_6b0501: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins zero = {0};
    }

    mstatus_vs_active_6b0501: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active = {[1:3]};
    }

    cp_ssstrictv_ls_eew_lt_sewmin_vl0: cross vtype_prev_vill_clear, vl_zero_6b0501, mstatus_vs_active_6b0501, ls_eew_below_sewmin;

    // Edge case: still reserved when vstart >= vl
    vstart_ge_vl_6b0501: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")) {
        bins true = {1'b1};
    }

    cp_ssstrictv_ls_eew_lt_sewmin_vstart_ge_vl: cross vtype_prev_vill_clear, vl_nonzero, mstatus_vs_active_6b0501, vstart_ge_vl_6b0501, ls_eew_below_sewmin;
    `endif

//// end cp_ssstrictv_ls_eew_lt_sewmin ///////////////////////////////////////////////////////////
