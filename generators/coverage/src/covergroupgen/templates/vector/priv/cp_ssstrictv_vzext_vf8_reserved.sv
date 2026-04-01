// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vzext_vf8_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vzext.vf8: source EEW = SEW/8, source EMUL = LMUL/8
    // Reserved when source EEW < 8 (SEW<=32) or source EMUL < 1/8 (LMUL<=mf2)

    sew_reserved_vf8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins sew8  = {0};
        bins sew16 = {1};
        bins sew32 = {2};
    }

    lmul_reserved_vf8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins mf8 = {5};
        bins mf4 = {6};
        bins mf2 = {7};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_vzext_vf8_bad_eew: cross std_trap_vec, sew_reserved_vf8, trap_occurred;

    cp_ssstrictv_vzext_vf8_bad_emul: cross std_trap_vec, lmul_reserved_vf8, trap_occurred;

//// end cp_ssstrictv_vzext_vf8_reserved ///////////////////////////////////////////////////////////
