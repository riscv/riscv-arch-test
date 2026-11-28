    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ls_indexed_msb_ei16
    //////////////////////////////////////////////////////////////////////////////////

    // Index element 0 has its top bit set, so it must be zero-extended to XLEN
    vs2_element_zero_msb_ei16 : coverpoint get_vr_element_zero_eew(ins.hart, ins.issue, ins.current.vs2_val, 16) {
        bins msb_set = {[16'h8000:16'hFFFF]};
    }

    cp_custom_ls_indexed_msb_ei16 : cross std_vec, vs2_element_zero_msb_ei16;

    //// end cp_custom_ls_indexed_msb_ei16 ////////////////////////////////////////////////
