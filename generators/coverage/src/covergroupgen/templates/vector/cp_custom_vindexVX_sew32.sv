    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vindexVX_rs1_not_truncated_64
    //////////////////////////////////////////////////////////////////////////////////

    `ifdef XLEN64

    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    vs2_element_zero_nonzero : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31:0] {
        wildcard bins sew32     = {[32'b11111111_11111111_11111111_11111111:32'b00000000_00000000_00000000_00000001]};
    }

    rs1_target_value : coverpoint ins.current.rs1_val == 64'h8000000000000001 {
        bins target = {1};
    }

    cp_custom_vindexVX_rs1_not_truncated_64 : cross std_vec, rs1_target_value, vs2_element_zero_nonzero;

    `endif

    //// end cp_custom_vindexVX_rs1_not_truncated_64////////////////////////////////////////////////
