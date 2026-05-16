// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vmvnr_simm_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Reserved simm[4:0] values (not 0, 1, 3, or 7)
    simm_reserved: coverpoint ins.current.insn[19:15] {
        ignore_bins valid_0 = {5'b00000};
        ignore_bins valid_1 = {5'b00001};
        ignore_bins valid_3 = {5'b00011};
        ignore_bins valid_7 = {5'b00111};
    }

    cp_ssstrictv_vmvnr_simm_reserved: cross std_trap_vec, simm_reserved;

//// end cp_ssstrictv_vmvnr_simm_reserved /////////////////////////////////////////////////////////////
