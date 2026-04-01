// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_idx_emul_lt_f8
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Index EMUL = (index_EEW / SEW) * LMUL < 1/8 (reserved) for indexed load/store
    vtype_width_idx_emul_lt_f8 : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                  coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                                  coverpoint ins.current.insn[14:12]} {
        // Index EEW=8 (width=000): EMUL = (8/SEW)*LMUL
        `ifdef LMULf8_SUPPORTED
        `ifdef SEW16_SUPPORTED
        bins eew8_sew16_lmulf8  = {3'b101, 2'b01, 3'b000};  // (8/16)*(1/8) = 1/16
        `endif
        `ifdef SEW32_SUPPORTED
        bins eew8_sew32_lmulf8  = {3'b101, 2'b10, 3'b000};  // (8/32)*(1/8) = 1/32
        `endif
        `ifdef SEW64_SUPPORTED
        bins eew8_sew64_lmulf8  = {3'b101, 2'b11, 3'b000};  // (8/64)*(1/8) = 1/64
        `endif
        `endif
        `ifdef LMULf4_SUPPORTED
        `ifdef SEW32_SUPPORTED
        bins eew8_sew32_lmulf4  = {3'b110, 2'b10, 3'b000};  // (8/32)*(1/4) = 1/16
        `endif
        `ifdef SEW64_SUPPORTED
        bins eew8_sew64_lmulf4  = {3'b110, 2'b11, 3'b000};  // (8/64)*(1/4) = 1/32
        `endif
        `endif
        `ifdef LMULf2_SUPPORTED
        `ifdef SEW64_SUPPORTED
        bins eew8_sew64_lmulf2  = {3'b111, 2'b11, 3'b000};  // (8/64)*(1/2) = 1/16
        `endif
        `endif

        // Index EEW=16 (width=101): EMUL = (16/SEW)*LMUL
        `ifdef LMULf8_SUPPORTED
        `ifdef SEW32_SUPPORTED
        bins eew16_sew32_lmulf8 = {3'b101, 2'b10, 3'b101};  // (16/32)*(1/8) = 1/16
        `endif
        `ifdef SEW64_SUPPORTED
        bins eew16_sew64_lmulf8 = {3'b101, 2'b11, 3'b101};  // (16/64)*(1/8) = 1/32
        `endif
        `endif
        `ifdef LMULf4_SUPPORTED
        `ifdef SEW64_SUPPORTED
        bins eew16_sew64_lmulf4 = {3'b110, 2'b11, 3'b101};  // (16/64)*(1/4) = 1/16
        `endif
        `endif

        // Index EEW=32 (width=110): EMUL = (32/SEW)*LMUL
        `ifdef LMULf8_SUPPORTED
        `ifdef SEW64_SUPPORTED
        bins eew32_sew64_lmulf8 = {3'b101, 2'b11, 3'b110};  // (32/64)*(1/8) = 1/16
        `endif
        `endif
    }

    cp_ssstrictv_ls_idx_emul_lt_f8: cross std_trap_vec, vtype_width_idx_emul_lt_f8;

//// end cp_ssstrictv_ls_idx_emul_lt_f8 ///////////////////////////////////////////////////////////////
