// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vstart_ge_vlmax
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vstart >= VLMAX is reserved (out of bounds for current vtype)
    vstart_ge_vlmax: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                                 get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins true = {1'b1};
    }

    vtype_valid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vstart_ge_vlmax: cross vstart_ge_vlmax, vtype_valid, trap_occurred;

//// end cp_ssstrictv_vstart_ge_vlmax ///////////////////////////////////////////////////////////////////
