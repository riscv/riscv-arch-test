
    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    lmul_1_through_4 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
    }

    vs2_eq_vs1: coverpoint ins.current.vs1 == ins.current.vs2 {
        bins equal = {1'b1};
    }

    cp_ssstrictv_widening_source_overlap : cross std_trap_vec, lmul_1_through_4, vs2_eq_vs1;
