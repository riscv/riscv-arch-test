//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vshift_upperbits_rs1_ones
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector shift instructions with vv operands

    // ensures vd updates
    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;


    rs1_top_bits_one_cross_sew32 : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],  ins.current.rs1_val} {
        `ifdef XLEN32
        wildcard bins sew32     = {34'b10_11111111_11111111_11111111_111?????};
        `endif

        `ifdef XLEN64
        wildcard bins sew32     = {66'b10_????????_????????_????????_????????_11111111_11111111_11111111_111?????};
        `endif
    }

    cp_custom_vshift_upperbits_rs1_ones : cross std_vec, rs1_top_bits_one_cross_sew32;

    //// end cp_custom_vshift_upperbits_rs1_ones////////////////////////////////////////////////
