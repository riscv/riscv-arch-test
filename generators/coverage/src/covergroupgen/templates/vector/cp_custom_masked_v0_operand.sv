    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_masked_v0_operand
    //////////////////////////////////////////////////////////////////////////////////

    // Verify indexed LS instructions run correctly when masked (vm=0) and
    // vs2 (the index vector) is v0, so v0 serves as both mask and source.

    // Masking enabled (vm=0, bit 25 = 0)
    mask_enabled: coverpoint ins.current.insn[25] {
        bins masked = {1'b0};
    }

    // vs2 is v0 (bits 24:20 = 0)
    vs2_v0: coverpoint ins.current.insn[24:20] {
        bins v0 = {5'b00000};
    }

    // vd is NOT v0 (required for most instructions when masked)
    vd_not_v0: coverpoint ins.current.insn[11:7] {
        bins not_v0 = {[1:31]};
    }

    // Cross: masked with vs2=v0 (v0 serves as both mask and index source)
    cp_custom_masked_vs2_v0: cross std_vec, mask_enabled, vs2_v0, vd_not_v0;

    //// end cp_custom_masked_v0_operand////////////////////////////////////////////////
