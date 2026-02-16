//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vshift_upperbits_vs1_ones
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector shift instructions with vv operands

    // ensures vd updates
    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;


    vs1_top_bits_one_sew16 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],  get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)} {
        wildcard bins sew16     = {66'b01_????????_????????_????????_????????_????????_????????_11111111_1111????};
    }


    cp_custom_vshift_upperbits_vs1_ones : cross std_vec, vs1_top_bits_one_sew16;

    //// end cp_custom_vshift_upperbits_vs1_ones////////////////////////////////////////////////
