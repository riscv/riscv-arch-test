// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_widening_source_overlap
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Widening with vs2 == vs1: same register read at different EEWs, must trap
    vtype_lmul_widen_src: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins half = {7};
        bins one  = {0};
        bins two  = {1};
        bins four = {2};
    }

    trap_occurred_9b660f: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == 2) {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_widening_source_overlap: cross std_trap_vec, vtype_lmul_widen_src, vs2_eq_vs1, trap_occurred_9b660f;

//// end cp_ssstrictv_widening_source_overlap ///////////////////////////////////////////////////////////////
