// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_eew_lt_sewmin
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Vector load/store EEW (from width field) smaller than SEWMIN is reserved
    ls_eew_below_sewmin: coverpoint ins.current.insn[14:12] {
        `ifndef SEW8_SUPPORTED
        bins eew8  = {3'b000};  // width=000 -> EEW=8, reserved if SEWMIN > 8
        `endif
        `ifndef SEW16_SUPPORTED
        bins eew16 = {3'b101};  // width=101 -> EEW=16, reserved if SEWMIN > 16
        `endif
        `ifndef SEW32_SUPPORTED
        bins eew32 = {3'b110};  // width=110 -> EEW=32, reserved if SEWMIN > 32
        `endif
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_ls_eew_lt_sewmin: cross std_trap_vec, ls_eew_below_sewmin, trap_occurred;

    // Edge case: still reserved when vl=0
    vl_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins zero = {0};
    }

    mstatus_vs_active: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active[] = {[1:3]};
    }

    cp_ssstrictv_ls_eew_lt_sewmin_vl0: cross vtype_prev_vill_clear, vl_zero, mstatus_vs_active, ls_eew_below_sewmin, trap_occurred;

    // Edge case: still reserved when vstart >= vl
    vstart_ge_vl: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")) {
        bins true = {1'b1};
    }

    cp_ssstrictv_ls_eew_lt_sewmin_vstart_ge_vl: cross vtype_prev_vill_clear, vl_nonzero, mstatus_vs_active, vstart_ge_vl, ls_eew_below_sewmin, trap_occurred;

//// end cp_ssstrictv_ls_eew_lt_sewmin ///////////////////////////////////////////////////////////
