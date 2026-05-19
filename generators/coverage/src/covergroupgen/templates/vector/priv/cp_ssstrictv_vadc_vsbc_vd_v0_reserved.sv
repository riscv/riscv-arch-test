// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vadc_vsbc_vd_v0_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vadc (funct6=010000) or vsbc (funct6=010010) with vd=v0 (reserved)
    vadc_funct6: coverpoint ins.current.insn[31:26] {
        bins vadc = {6'b010000};
    }

    vsbc_funct6: coverpoint ins.current.insn[31:26] {
        bins vsbc = {6'b010010};
    }

    cp_ssstrictv_vadc_vd_v0_reserved: cross std_trap_vec, vadc_funct6, vd_v0;
    cp_ssstrictv_vsbc_vd_v0_reserved: cross std_trap_vec, vsbc_funct6, vd_v0;

//// end cp_ssstrictv_vadc_vsbc_vd_v0_reserved /////////////////////////////////////////////////////////////
