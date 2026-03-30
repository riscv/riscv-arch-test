    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_red
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector reduction widening instructions

    // ensures vd updates
    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;
    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {2};
    }

    vtype_lmul_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {3};
    }

    vd_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vd_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vd_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    vs1_reg_aligned_lmul_2: coverpoint ins.current.insn[19:15] {
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vs1_reg_aligned_lmul_4: coverpoint ins.current.insn[19:15] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vs1_reg_aligned_lmul_8: coverpoint ins.current.insn[19:15] {
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vs2_reg_aligned_lmul_2: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vs2_reg_aligned_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vs2_reg_aligned_lmul_8: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vd_reg_aligned_lmul_2: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vd_reg_aligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vd_reg_aligned_lmul_8: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vs1_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vs1_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vs1_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    cp_custom_voffgroup_vd_lmul2:     cross std_vec, vtype_lmul_2, vd_all_reg_unaligned_lmul_2,     vs1_reg_aligned_lmul_2,         vs2_reg_aligned_lmul_2;
    cp_custom_voffgroup_vd_lmul4:     cross std_vec, vtype_lmul_4, vd_all_reg_unaligned_lmul_4,     vs1_reg_aligned_lmul_4,         vs2_reg_aligned_lmul_4;
    cp_custom_voffgroup_vd_lmul8:     cross std_vec, vtype_lmul_8, vd_all_reg_unaligned_lmul_8,     vs1_reg_aligned_lmul_8,         vs2_reg_aligned_lmul_8;

    cp_custom_voffgroup_vs1_lmul2:    cross std_vec, vtype_lmul_2, vd_reg_aligned_lmul_2,           vs1_all_reg_unaligned_lmul_2,   vs2_reg_aligned_lmul_2;
    cp_custom_voffgroup_vs1_lmul4:    cross std_vec, vtype_lmul_4, vd_reg_aligned_lmul_4,           vs1_all_reg_unaligned_lmul_4,   vs2_reg_aligned_lmul_4;
    cp_custom_voffgroup_vs1_lmul8:    cross std_vec, vtype_lmul_8, vd_reg_aligned_lmul_8,           vs1_all_reg_unaligned_lmul_8,   vs2_reg_aligned_lmul_8;


    vl_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        // Any value between max and 1
        bins one = {1};
    }

    v0_element0_masked : coverpoint (ins.current.v0_val[0]) {
        bins one = {1};
    }

    vd_ne_vs1 : coverpoint (ins.current.insn[19:15] != ins.current.insn[11:7]) {
        bins target = {1'b1};
    }

    cp_custom_element0Masked : cross std_vec, vl_one, v0_element0_masked, vd_ne_vs1;


    vd_v0: coverpoint ins.current.insn[11:7] {
        bins zero = {5'b00000};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins enabled = {1'b0};
    }

    cp_custom_vmask_write_v0_masked:    cross std_vec, vd_v0, mask_enabled;

    //// end cp_custom_red ////////////////////////////////////////////////
