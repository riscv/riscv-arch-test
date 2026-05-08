// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vzext_vf4_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vzext.vf4: source EEW = SEW/4, source EMUL = LMUL/4
    // Reserved when source EEW < 8 (SEW<=16) or source EMUL < 1/8 (LMUL<=mf4)

    sew_reserved_vf4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins sew8  = {0};
        bins sew16 = {1};
    }

    lmul_reserved_vf4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins mf8 = {5};
        bins mf4 = {6};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vzext_vf4_bad_eew: cross std_trap_vec, sew_reserved_vf4, trap_occurred;

    cp_ssstrictv_vzext_vf4_bad_emul: cross std_trap_vec, lmul_reserved_vf4, trap_occurred;

//// end cp_ssstrictv_vzext_vf4_reserved ///////////////////////////////////////////////////////////
