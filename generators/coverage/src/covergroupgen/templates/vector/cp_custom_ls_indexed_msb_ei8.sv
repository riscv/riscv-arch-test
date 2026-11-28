    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ls_indexed_msb_ei8
    //////////////////////////////////////////////////////////////////////////////////

    // Index element 0 has its top bit set, so it must be zero-extended to XLEN
    vs2_element_zero_msb_ei8 : coverpoint get_vr_element_zero_eew(ins.hart, ins.issue, ins.current.vs2_val, 8) {
        bins msb_set = {[8'h80:8'hFF]};
    }

    cp_custom_ls_indexed_msb_ei8 : cross std_vec, vs2_element_zero_msb_ei8;

    //// end cp_custom_ls_indexed_msb_ei8 ////////////////////////////////////////////////
