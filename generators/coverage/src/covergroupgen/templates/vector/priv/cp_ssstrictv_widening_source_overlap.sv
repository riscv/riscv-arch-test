// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_widening_source_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Widening with vs2 == vs1: same register read at different EEWs, must trap
    vtype_lmul_widen_src: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins half = {7};
        bins one  = {0};
        bins two  = {1};
        bins four = {2};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_widening_source_overlap: cross std_trap_vec, vtype_lmul_widen_src, vs2_eq_vs1, trap_occurred;

//// end cp_ssstrictv_widening_source_overlap ///////////////////////////////////////////////////////////////
