// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_idx_emul_gt8
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Index EMUL = (index_EEW / SEW) * LMUL > 8 (reserved) for indexed load/store
    vtype_width_idx_emul_gt8 : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                                coverpoint ins.current.insn[14:12]} {
        // Index EEW=16 (width=101): EMUL = (16/SEW)*LMUL
        bins eew16_sew8_lmul8  = {3'b011, 2'b00, 3'b101};  // (16/8)*8 = 16

        // Index EEW=32 (width=110): EMUL = (32/SEW)*LMUL
        bins eew32_sew8_lmul4  = {3'b010, 2'b00, 3'b110};  // (32/8)*4 = 16
        bins eew32_sew8_lmul8  = {3'b011, 2'b00, 3'b110};  // (32/8)*8 = 32
        bins eew32_sew16_lmul8 = {3'b011, 2'b01, 3'b110};  // (32/16)*8 = 16

        // Index EEW=64 (width=111): EMUL = (64/SEW)*LMUL
        bins eew64_sew8_lmul2  = {3'b001, 2'b00, 3'b111};  // (64/8)*2 = 16
        bins eew64_sew8_lmul4  = {3'b010, 2'b00, 3'b111};  // (64/8)*4 = 32
        bins eew64_sew8_lmul8  = {3'b011, 2'b00, 3'b111};  // (64/8)*8 = 64
        bins eew64_sew16_lmul4 = {3'b010, 2'b01, 3'b111};  // (64/16)*4 = 16
        bins eew64_sew16_lmul8 = {3'b011, 2'b01, 3'b111};  // (64/16)*8 = 32
        bins eew64_sew32_lmul8 = {3'b011, 2'b10, 3'b111};  // (64/32)*8 = 16
    }

    cp_ssstrictv_ls_idx_emul_gt8: cross std_trap_vec, vtype_width_idx_emul_gt8;

//// end cp_ssstrictv_ls_idx_emul_gt8 /////////////////////////////////////////////////////////////////
