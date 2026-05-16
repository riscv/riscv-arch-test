// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vfp_frm_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Vector FP instruction with invalid frm (reserved rounding modes 5, 6, 7)

    frm_invalid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm") {
        bins reserved_5 = {3'b101};
        bins reserved_6 = {3'b110};
        bins reserved_7 = {3'b111};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    // Standard case: frm invalid with normal vector conditions (vill=0, vstart=0, vl!=0)
    cp_ssstrictv_vfp_frm_reserved: cross std_trap_vec, frm_invalid, trap_occurred;

    // Edge case: frm invalid with vl=0 (spec says still reserved)
    vl_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins zero = {0};
    }

    mstatus_vs_active: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active[] = {[1:3]};
    }

    cp_ssstrictv_vfp_frm_reserved_vl0: cross vtype_prev_vill_clear, vl_zero, mstatus_vs_active, frm_invalid, trap_occurred;

    // Edge case: frm invalid with vstart >= vl (spec says still reserved)
    vstart_ge_vl: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")) {
        bins true = {1'b1};
    }

    cp_ssstrictv_vfp_frm_reserved_vstart_ge_vl: cross vtype_prev_vill_clear, vl_nonzero, mstatus_vs_active, vstart_ge_vl, frm_invalid, trap_occurred;

//// end cp_ssstrictv_vfp_frm_reserved ///////////////////////////////////////////////////////////
