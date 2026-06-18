
    // cp_custom_vindexCorners: vrgather/vslidedown index corner cases
    // Local validity check (std_vec may not be present in isolated covergroups)
    vindexCorners_valid: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0
    } {
        bins true = {1'b1};
    }

    vtype_sew_elemt_zero_vs1_all_ones : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],  get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)} {
        `ifdef SEW8_SUPPORTED
        wildcard bins sew8      = {66'b00_????????_????????_????????_????????_????????_????????_????????_11111111};
        `endif
        `ifdef SEW16_SUPPORTED
        wildcard bins sew16     = {66'b01_????????_????????_????????_????????_????????_????????_11111111_11111111};
        `endif
        `ifdef SEW32_SUPPORTED
        wildcard bins sew32     = {66'b10_????????_????????_????????_????????_11111111_11111111_11111111_11111111};
        `endif
        `ifdef SEW64_SUPPORTED
        wildcard bins sew64     = {66'b11_11111111_11111111_11111111_11111111_11111111_11111111_11111111_11111111};
        `endif
    }

    cp_custom_vindexCorners_index_ge_vlmax : cross vindexCorners_valid, vtype_sew_elemt_zero_vs1_all_ones;

    //////////////////////////////////////////////////////////////////////////////////

    vindexCorners_vl_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins one = {1};
    }

    vindexCorners_vtype_lmul_2 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vtype_sew_elemt_zero_vs1_2 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],  get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)} {
        `ifdef SEW8_SUPPORTED
        wildcard bins sew8      = {66'b00_????????_????????_????????_????????_????????_????????_????????_00000010};
        `endif
        `ifdef SEW16_SUPPORTED
        wildcard bins sew16     = {66'b01_????????_????????_????????_????????_????????_????????_00000000_00000010};
        `endif
        `ifdef SEW32_SUPPORTED
        wildcard bins sew32     = {66'b10_????????_????????_????????_????????_00000000_00000000_00000000_00000010};
        `endif
        `ifdef SEW64_SUPPORTED
        wildcard bins sew64     = {66'b11_00000000_00000000_00000000_00000000_00000000_00000000_00000000_00000010};
        `endif
    }

    cp_custom_vindexCorners_index_gt_vl_lt_vlmax :   cross vindexCorners_valid, vindexCorners_vl_one, vindexCorners_vtype_lmul_2, vtype_sew_elemt_zero_vs1_2;
