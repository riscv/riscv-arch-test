//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vindexVX_rs1_not_truncated_64
    //////////////////////////////////////////////////////////////////////////////////




    vs2_element_zero_nonzero_sew16 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31:0] {
        wildcard bins sew16     = {[32'b????????_????????_11111111_11111111:32'b????????_????????_00000000_00000001]};
    }

    `ifdef XLEN32

    rs1_target_value : coverpoint ins.current.rs1_val == 32'h80000001 {
        bins target = {1};
    }

    cp_custom_vindexVX_rs1_not_truncated_32 : cross std_vec, rs1_target_value, vs2_element_zero_nonzero_sew16;

    `endif

    //////////////////////////////////////////////////////////////////////////////////

    `ifdef XLEN64

    rs1_target_value : coverpoint ins.current.rs1_val == 64'h8000000000000001 {
        bins target = {1};
    }

    cp_custom_vindexVX_rs1_not_truncated_64 : cross std_vec, rs1_target_value, vs2_element_zero_nonzero_sew16;

    `endif

    //// end cp_custom_vindexVX_rs1_not_truncated_64////////////////////////////////////////////////
