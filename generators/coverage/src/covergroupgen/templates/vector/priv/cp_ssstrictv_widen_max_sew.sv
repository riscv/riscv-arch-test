// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_widen_max_sew
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Widening at MAX_SEW: destination EEW = 2*SEW > ELEN, must trap
    // Covers all widening instructions (including widening reductions)
    // Tests all legal widening LMUL values (1-4) crossed with all supported SEWs

    vtype_lmul_widen: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one  = {0};
        bins two  = {1};
        bins four = {2};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_widen_max_sew: cross std_trap_vec, vtype_all_sew_supported, vtype_lmul_widen, trap_occurred;

//// end cp_ssstrictv_widen_max_sew /////////////////////////////////////////////////////////////////////////
