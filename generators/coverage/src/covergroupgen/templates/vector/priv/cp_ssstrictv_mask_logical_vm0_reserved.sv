// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_mask_logical_vm0_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Vector mask logical instructions with vm=0 (reserved masked encoding)
    mask_logical_funct6: coverpoint ins.current.insn[31:26] {
        bins vmand   = {6'b011001};
        bins vmnand  = {6'b011101};
        bins vmandn  = {6'b011000};
        bins vmxor   = {6'b011011};
        bins vmor    = {6'b011010};
        bins vmnor   = {6'b011110};
        bins vmorn   = {6'b011100};
        bins vmxnor  = {6'b011111};
    }

    vm_masked: coverpoint ins.current.insn[25] {
        bins masked = {1'b0};
    }

    cp_ssstrictv_mask_logical_vm0_reserved: cross std_trap_vec, mask_logical_funct6, vm_masked;

//// end cp_ssstrictv_mask_logical_vm0_reserved ////////////////////////////////////////////////////////////
