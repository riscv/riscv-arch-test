    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vindexVX_rs1_not_truncated_64
    //////////////////////////////////////////////////////////////////////////////////

    `ifdef UDB_MXLEN_64

    vs2_element_zero_nonzero : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31:0] {
        bins sew32     = {[32'h0000_0001:32'hFFFF_FFFF]};
    }

    rs1_target_value : coverpoint ins.current.rs1_val == 64'h8000000000000001 {
        bins target = {1};
    }

    cp_custom_vindexVX_rs1_not_truncated_64 : cross std_vec, rs1_target_value, vs2_element_zero_nonzero;

    `endif

    //// end cp_custom_vindexVX_rs1_not_truncated_64////////////////////////////////////////////////
