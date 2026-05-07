// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vfp_eew_unsupported
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Vector FP operand EEW (=SEW) not a supported FP type width (includes FLEN < SEW)

    sew_unsupported_fp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        // SEW=8 (vsew=0) is never a supported FP width
        bins sew8 = {0};
        `ifndef D_COVERAGE
        // SEW=64 (vsew=3) unsupported without D extension (FLEN < 64)
        bins sew64 = {3};
        `endif
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vfp_eew_unsupported: cross std_trap_vec, sew_unsupported_fp, trap_occurred;

    // Edge case: still reserved when vl=0
    vl_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins zero = {0};
    }

    mstatus_vs_active: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active[] = {[1:3]};
    }

    cp_ssstrictv_vfp_eew_unsupported_vl0: cross vtype_prev_vill_clear, vl_zero, mstatus_vs_active, sew_unsupported_fp, trap_occurred;

    // Edge case: still reserved when vstart >= vl
    vstart_ge_vl: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")) {
        bins true = {1'b1};
    }

    cp_ssstrictv_vfp_eew_unsupported_vstart_ge_vl: cross vtype_prev_vill_clear, vl_nonzero, mstatus_vs_active, vstart_ge_vl, sew_unsupported_fp, trap_occurred;

//// end cp_ssstrictv_vfp_eew_unsupported ///////////////////////////////////////////////////////////
