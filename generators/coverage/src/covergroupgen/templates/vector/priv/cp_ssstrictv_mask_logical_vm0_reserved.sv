// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_mask_logical_vm0_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Vector mask logical instructions (vmand/vmnand/vmandn/vmor/vmnor/vmorn/vmxor/vmxnor) with vm=0 (reserved).
    // Use a single union bin covering all 8 funct6 values so each per-instruction cg only sees the bin
    // matching its own funct6 (the others are "unreachable" by construction; the union bin makes them count once).
    mask_logical_funct6: coverpoint ins.current.insn[31:26] {
        bins mask_logical = {6'b011001, 6'b011101, 6'b011000, 6'b011011,
                              6'b011010, 6'b011110, 6'b011100, 6'b011111};
    }

    vm_masked: coverpoint ins.current.insn[25] {
        bins masked = {1'b0};
    }

    cp_ssstrictv_mask_logical_vm0_reserved: cross std_trap_vec, mask_logical_funct6, vm_masked;

//// end cp_ssstrictv_mask_logical_vm0_reserved ////////////////////////////////////////////////////////////
