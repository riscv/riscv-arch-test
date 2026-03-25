    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_voffgroup_vd_lmul2/4/8
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for vmv.s.x

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

    cp_custom_voffgroup_vd_lmul2:     cross std_vec, vtype_lmul_2, vd_all_reg_unaligned_lmul_2;
    cp_custom_voffgroup_vd_lmul4:     cross std_vec, vtype_lmul_4, vd_all_reg_unaligned_lmul_4;
    cp_custom_voffgroup_vd_lmul8:     cross std_vec, vtype_lmul_8, vd_all_reg_unaligned_lmul_8;

    //// end cp_custom_voffgroup_vd_lmul2/4/8 ////////////////////////////////////////////////
