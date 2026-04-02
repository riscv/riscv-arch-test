// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_seg_vd_overflow_emulgt1
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Segment load/store where vd + NFIELDS * LMUL > 32 with LMUL > 1
    vd_nf_lmul_overflow : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                           coverpoint ins.current.insn[31:29],
                           coverpoint ins.current.insn[11:7]} {
        // LMUL=2, nf=2 (4 regs): vd=30 overflows (30+4=34)
        bins lmul2_nf2_vd30 = {3'b001, 3'b001, 5'd30};
        // LMUL=2, nf=3 (6 regs): vd=28,30 overflow
        bins lmul2_nf3_vd28 = {3'b001, 3'b010, 5'd28};
        bins lmul2_nf3_vd30 = {3'b001, 3'b010, 5'd30};
        // LMUL=2, nf=4 (8 regs): vd=26,28,30 overflow
        bins lmul2_nf4_vd26 = {3'b001, 3'b011, 5'd26};
        bins lmul2_nf4_vd28 = {3'b001, 3'b011, 5'd28};
        bins lmul2_nf4_vd30 = {3'b001, 3'b011, 5'd30};
        // LMUL=4, nf=2 (8 regs): vd=28 overflows (28+8=36)
        bins lmul4_nf2_vd28 = {3'b010, 3'b001, 5'd28};
    }

    cp_ssstrictv_ls_seg_vd_overflow_emulgt1: cross std_trap_vec, vtype_sew_supported, vd_nf_lmul_overflow;

//// end cp_ssstrictv_ls_seg_vd_overflow_emulgt1 /////////////////////////////////////////////////////////
