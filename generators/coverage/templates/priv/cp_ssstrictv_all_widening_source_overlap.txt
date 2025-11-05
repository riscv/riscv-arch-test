    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    lmul_1_through_4 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
    }

    cp_ssstrictv_widening_source_overlap : cross std_trap_vec, lmul_1_through_4, vs1_all_reg, vs2_all_reg, vd_all_reg_aligned_lmul_2;
