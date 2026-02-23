
    vtype_lmul_sew_emulf16 : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0]} {
        bins lmulf8_sew32 = {3'b101, 2'b10};
        bins lmulf4_sew64 = {3'b110, 2'b11};
    }

    cp_ssstrictv_vrgatherei16_emul_f16 : cross std_trap_vec, vd_ne_vs1, vd_ne_vs2, vtype_lmul_sew_emulf16,
                                                            vs1_reg_aligned_lmul_8, vs2_reg_aligned_lmul_8, d_reg_aligned_lmul_8;
