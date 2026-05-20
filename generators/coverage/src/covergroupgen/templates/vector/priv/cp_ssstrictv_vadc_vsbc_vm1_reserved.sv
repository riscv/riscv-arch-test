// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vadc_vsbc_vm1_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vadc/vmadc/vsbc/vmsbc with vm=1 (unmasked, reserved for these masked-only forms).
    // funct6 covers all four (010000=vadc, 010001=vmadc, 010010=vsbc, 010011=vmsbc).
    funct6_carry_borrow: coverpoint ins.current.insn[31:26] {
        bins op = {6'b010000, 6'b010001, 6'b010010, 6'b010011};
    }

    vm_unmasked: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b1};
    }

    cp_ssstrictv_vadc_vsbc_vm1_reserved : cross std_trap_vec, funct6_carry_borrow, vm_unmasked;

//// end cp_ssstrictv_vadc_vsbc_vm1_reserved /////////////////////////////////////////////////////////////
