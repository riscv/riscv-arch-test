
    // cp_custom_vindexCorners (SEW=64): vrgather/vslidedown index corner cases
    vindexCorners_valid: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) != 0
    } {
        bins true = {1'b1};
    }

    vtype_sew_elemt_zero_vs1_all_ones : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew")[1:0],  get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)} {
        wildcard bins sew64     = {66'b11_11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111};
    }

    cp_custom_vindexCorners_index_ge_vlmax : cross vindexCorners_valid, vtype_sew_elemt_zero_vs1_all_ones;

    //////////////////////////////////////////////////////////////////////////////////

    vindexCorners_vl_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) {
        bins one = {1};
    }

    vindexCorners_vtype_lmul_2 : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vlmul") {
        bins two = {1};
    }

    vtype_sew_elemt_zero_vs1_2 : coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew")[1:0],  get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)} {
        wildcard bins sew64     = {66'b11_00000000_00000000_00000000_00000000_00000000_00000000_00000000_00000010};
    }

    cp_custom_vindexCorners_index_gt_vl_lt_vlmax :   cross vindexCorners_valid, vindexCorners_vl_one, vindexCorners_vtype_lmul_2, vtype_sew_elemt_zero_vs1_2;
