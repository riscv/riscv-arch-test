// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vzext_src_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vzext source EEW not supported or source EMUL below minimum legal LMUL (1/8)

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    // vzext variant from vs1 field: vf2=6, vf4=4, vf8=2
    vzext_vf2: coverpoint ins.current.insn[19:15] {
        bins vf2 = {5'd6};
    }

    vzext_vf4: coverpoint ins.current.insn[19:15] {
        bins vf4 = {5'd4};
    }

    vzext_vf8: coverpoint ins.current.insn[19:15] {
        bins vf8 = {5'd2};
    }

    // Source EEW unsupported: SEW/N < 8
    // vf2: SEW=8 -> src_EEW=4 (unsupported)
    sew_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e8 = {0};
    }

    // vf4: SEW=8 -> src_EEW=2, SEW=16 -> src_EEW=4 (both unsupported)
    sew_8_or_16: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e8 = {0};
        bins e16 = {1};
    }

    // vf8: SEW=8 -> src_EEW=1, SEW=16 -> src_EEW=2, SEW=32 -> src_EEW=4 (all unsupported)
    sew_8_16_or_32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e8 = {0};
        bins e16 = {1};
        bins e32 = {2};
    }

    // Source EMUL too small: LMUL/N < 1/8
    // vf2: LMUL=mf8(5) -> EMUL=1/16
    `ifdef LMULf8_SUPPORTED
    lmul_mf8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins mf8 = {5};
    }
    `endif

    // vf4: LMUL=mf8(5) -> EMUL=1/32, LMUL=mf4(6) -> EMUL=1/16
    lmul_mf8_or_mf4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        `ifdef LMULf8_SUPPORTED
        bins mf8 = {5};
        `endif
        `ifdef LMULf4_SUPPORTED
        bins mf4 = {6};
        `endif
    }

    // vf8: LMUL=mf8(5) -> EMUL=1/64, LMUL=mf4(6) -> EMUL=1/32, LMUL=mf2(7) -> EMUL=1/16
    lmul_mf8_mf4_or_mf2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        `ifdef LMULf8_SUPPORTED
        bins mf8 = {5};
        `endif
        `ifdef LMULf4_SUPPORTED
        bins mf4 = {6};
        `endif
        `ifdef LMULf2_SUPPORTED
        bins mf2 = {7};
        `endif
    }

    // Source EEW unsupported crosses
    cp_ssstrictv_vzext_vf2_src_eew: cross std_trap_vec, vzext_vf2, sew_8, trap_occurred;
    cp_ssstrictv_vzext_vf4_src_eew: cross std_trap_vec, vzext_vf4, sew_8_or_16, trap_occurred;
    cp_ssstrictv_vzext_vf8_src_eew: cross std_trap_vec, vzext_vf8, sew_8_16_or_32, trap_occurred;

    // Source EMUL below minimum crosses
    `ifdef LMULf8_SUPPORTED
    cp_ssstrictv_vzext_vf2_src_emul: cross std_trap_vec, vzext_vf2, lmul_mf8, trap_occurred;
    `endif
    cp_ssstrictv_vzext_vf4_src_emul: cross std_trap_vec, vzext_vf4, lmul_mf8_or_mf4, trap_occurred;
    cp_ssstrictv_vzext_vf8_src_emul: cross std_trap_vec, vzext_vf8, lmul_mf8_mf4_or_mf2, trap_occurred;

//// end cp_ssstrictv_vzext_src_reserved ///////////////////////////////////////////////////////////
