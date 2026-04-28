    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vshift_upperbits_rs1_ones
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector shift instructions with vv operands

    // ensures vd updates
    // cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;
    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }


    rs1_top_bits_one_cross_sew : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],  ins.current.rs1_val} {
        `ifdef XLEN32
        wildcard bins sew64     = {34'b11_11111111_11111111_11111111_11??????};
        `endif

        `ifdef XLEN64
        wildcard bins sew64     = {66'b11_11111111_11111111_11111111_11111111_11111111_11111111_11111111_11??????};
        `endif
    }

    cp_custom_vshift_upperbits_rs1_ones : cross std_vec, rs1_top_bits_one_cross_sew;

    //// end cp_custom_vshift_upperbits_rs1_ones////////////////////////////////////////////////
