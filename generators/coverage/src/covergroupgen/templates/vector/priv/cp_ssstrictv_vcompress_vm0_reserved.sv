// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcompress_vm0_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vcompress (funct6=010111, funct3=010) with vm=0 is reserved
    vcompress_funct6_4db41a: coverpoint ins.current.insn[31:26] {
        bins vcompress = {6'b010111};
    }

    vcompress_funct3_4db41a: coverpoint ins.current.insn[14:12] {
        bins opmvv = {3'b010};
    }

    vm_masked: coverpoint ins.current.insn[25] {
        bins masked = {1'b0};
    }

    cp_ssstrictv_vcompress_vm0_reserved: cross std_trap_vec, vcompress_funct6_4db41a, vcompress_funct3_4db41a, vm_masked;

//// end cp_ssstrictv_vcompress_vm0_reserved ///////////////////////////////////////////////////////////////
