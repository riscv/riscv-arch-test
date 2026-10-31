// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_idx_emul_gt8
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Index EMUL = (index_EEW / SEW) * LMUL > 8 (reserved) for indexed load/store
    vtype_width_idx_emul_gt8 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                                ins.current.insn[14:12]} {
        // Index EEW=16 (width=101): EMUL = (16/SEW)*LMUL
        `ifdef MAXINDEXEEW_GE16
            bins eew16_sew8_lmul8  = {8'b011_00_101};  // (16/8)*8 = 16
        `endif

        // Index EEW=32 (width=110): EMUL = (32/SEW)*LMUL
        `ifdef MAXINDEXEEW_GE32
            bins eew32_sew8_lmul4  = {8'b010_00_110};  // (32/8)*4 = 16
            bins eew32_sew8_lmul8  = {8'b011_00_110};  // (32/8)*8 = 32
            bins eew32_sew16_lmul8 = {8'b011_01_110};  // (32/16)*8 = 16
        `endif

        // Index EEW=64 (width=111): EMUL = (64/SEW)*LMUL
        `ifdef MAXINDEXEEW_GE64
            bins eew64_sew8_lmul2  = {8'b001_00_111};  // (64/8)*2 = 16
            bins eew64_sew8_lmul4  = {8'b010_00_111};  // (64/8)*4 = 32
            bins eew64_sew8_lmul8  = {8'b011_00_111};  // (64/8)*8 = 64
            bins eew64_sew16_lmul4 = {8'b010_01_111};  // (64/16)*4 = 16
            bins eew64_sew16_lmul8 = {8'b011_01_111};  // (64/16)*8 = 32
            bins eew64_sew32_lmul8 = {8'b011_10_111};  // (64/32)*8 = 16
        `endif
    }

    cp_ssstrictv_ls_idx_emul_gt8: cross std_trap_vec, vtype_width_idx_emul_gt8;

//// end cp_ssstrictv_ls_idx_emul_gt8 /////////////////////////////////////////////////////////////////
