// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vadc_vsbc_vm1_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vadc (funct6=010000) or vsbc (funct6=010010) with vm=1 (unmasked, reserved)
    vadc_funct6_vm1: coverpoint ins.current.insn[31:26] {
        bins vadc = {6'b010000};
    }

    vsbc_funct6_9b440e: coverpoint ins.current.insn[31:26] {
        bins vsbc = {6'b010010};
    }

    vm_unmasked: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b1};
    }

    cp_ssstrictv_vadc_vm1_reserved : cross std_trap_vec, vadc_funct6_vm1, vm_unmasked;
    cp_ssstrictv_vsbc_vm1_reserved : cross std_trap_vec, vsbc_funct6_9b440e, vm_unmasked;

//// end cp_ssstrictv_vadc_vsbc_vm1_reserved /////////////////////////////////////////////////////////////
