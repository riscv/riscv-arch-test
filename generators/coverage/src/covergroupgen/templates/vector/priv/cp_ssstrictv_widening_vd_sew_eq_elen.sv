// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_widening_vd_sew_eq_elen
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Widening with SEW=ELEN: destination EEW = 2*SEW > ELEN, must trap
    // LMUL=1, registers chosen to avoid overlap traps (vd=8, vs2=10, vs1=12)

    vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_widening_vd_sew_eq_elen: cross std_trap_vec, vtype_all_sew_supported, vtype_lmul_1, trap_occurred;

//// end cp_ssstrictv_widening_vd_sew_eq_elen ////////////////////////////////////////////////////////////////
