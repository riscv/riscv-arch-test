    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vindexVX_rs1_not_truncated_64
    //////////////////////////////////////////////////////////////////////////////////

    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    vs2_element_zero_nonzero_sew8 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31:0] {
        wildcard bins sew8      = {[32'b????????_????????_????????_11111111:32'b????????_????????_????????_00000001]};
    }

    `ifdef XLEN32

    rs1_target_value : coverpoint ins.current.rs1_val == 32'h80000001 {
        bins target = {1};
    }

    cp_custom_vindexVX_rs1_not_truncated_32 : cross std_vec, rs1_target_value, vs2_element_zero_nonzero_sew8;

    `endif

    //////////////////////////////////////////////////////////////////////////////////

    `ifdef XLEN64

    rs1_target_value : coverpoint ins.current.rs1_val == 16'h8000000000000001 {
        bins target = {1};
    }

    cp_custom_vindexVX_rs1_not_truncated_64 : cross std_vec, rs1_target_value, vs2_element_zero_nonzero_sew8;

    `endif

    //// end cp_custom_vindexVX_rs1_not_truncated_64////////////////////////////////////////////////
