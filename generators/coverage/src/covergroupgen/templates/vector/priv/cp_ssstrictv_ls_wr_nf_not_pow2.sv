// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_wr_nf_not_pow2
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Whole-register store with nf encoding non-power-of-2 register count is reserved.
    nf_not_pow2 : coverpoint ins.current.insn[31:29] {
        bins three  = {3'b010};  // nf=2 -> NREG=3
        bins five   = {3'b100};  // nf=4 -> NREG=5
        bins six    = {3'b101};  // nf=5 -> NREG=6
        bins seven  = {3'b110};  // nf=6 -> NREG=7
    }

    cp_ssstrictv_ls_wr_nf_not_pow2 : cross std_trap_vec, nf_not_pow2;

//// end cp_ssstrictv_ls_wr_nf_not_pow2 ////////////////////////////////////////////////////////////
