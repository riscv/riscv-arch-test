// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_wr_nf_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Whole register load/store: nf+1 must be power of 2 and vd aligned to nf+1

    // nf values encoding non-power-of-2 register counts (3,5,6,7 regs)
    nf_not_pow2 : coverpoint ins.current.insn[31:29] {
        bins three  = {3'b010};  // nf=2 -> NREG=3
        bins five   = {3'b100};  // nf=4 -> NREG=5
        bins six    = {3'b101};  // nf=5 -> NREG=6
        bins seven  = {3'b110};  // nf=6 -> NREG=7
    }

    cp_ssstrictv_ls_wr_nf_not_pow2 : cross std_trap_vec, nf_not_pow2;

    // nf=1 (NREG=2): vd must be divisible by 2
    nf_nreg2 : coverpoint ins.current.insn[31:29] {
        bins nreg2 = {3'b001};
    }

    // nf=3 (NREG=4): vd must be divisible by 4
    nf_nreg4 : coverpoint ins.current.insn[31:29] {
        bins nreg4 = {3'b011};
    }

    // nf=7 (NREG=8): vd must be divisible by 8
    nf_nreg8 : coverpoint ins.current.insn[31:29] {
        bins nreg8 = {3'b111};
    }

    cp_ssstrictv_ls_wr_nreg2_vd_unaligned : cross std_trap_vec, nf_nreg2, vd_all_reg_unaligned_lmul_2;
    cp_ssstrictv_ls_wr_nreg4_vd_unaligned : cross std_trap_vec, nf_nreg4, vd_all_reg_unaligned_lmul_4;
    cp_ssstrictv_ls_wr_nreg8_vd_unaligned : cross std_trap_vec, nf_nreg8, vd_all_reg_unaligned_lmul_8;

//// end cp_ssstrictv_ls_wr_nf_reserved ///////////////////////////////////////////////////////////
