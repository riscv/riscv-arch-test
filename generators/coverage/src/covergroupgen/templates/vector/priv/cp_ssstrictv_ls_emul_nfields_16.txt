// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_emul_nfields_16
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // EMUL * NFIELDS = 16 (reserved) for segment loads/stores where EEW = SEW (EMUL = LMUL)
    vtype_lmul_nf_emul_nfields_16 : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                                     coverpoint ins.current.insn[31:29]} {
        bins lmul8_nf2 = {3'b011, 3'b001};  // LMUL=8, NFIELDS=2: 8*2=16
        bins lmul4_nf4 = {3'b010, 3'b011};  // LMUL=4, NFIELDS=4: 4*4=16
        bins lmul2_nf8 = {3'b001, 3'b111};  // LMUL=2, NFIELDS=8: 2*8=16
    }

    cp_ssstrictv_ls_emul_nfields_16: cross std_trap_vec, vtype_sew_supported, vtype_lmul_nf_emul_nfields_16;

//// end cp_ssstrictv_ls_emul_nfields_16 ///////////////////////////////////////////////////////////
