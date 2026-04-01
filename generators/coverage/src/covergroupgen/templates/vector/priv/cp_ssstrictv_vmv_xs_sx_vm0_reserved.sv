// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vmv_xs_sx_vm0_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vmv.x.s (funct6=010000, funct3=010) and vmv.s.x (funct6=010000, funct3=110) with vm=0 are reserved
    vmv_xs_sx_funct6: coverpoint ins.current.insn[31:26] {
        bins vmv = {6'b010000};
    }

    vmv_xs_sx_funct3: coverpoint ins.current.insn[14:12] {
        bins vmv_x_s = {3'b010};
        bins vmv_s_x = {3'b110};
    }

    vm_masked: coverpoint ins.current.insn[25] {
        bins masked = {1'b0};
    }

    cp_ssstrictv_vmv_xs_sx_vm0_reserved: cross std_trap_vec, vmv_xs_sx_funct6, vmv_xs_sx_funct3, vm_masked;

//// end cp_ssstrictv_vmv_xs_sx_vm0_reserved /////////////////////////////////////////////////////////////
