    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_slideOffsets
    //////////////////////////////////////////////////////////////////////////////////

    // Slide every element of a register group by 0, 1, 2, VLMAX/2, VLMAX-1, and VLMAX at vl = VLMAX
    slideOffsets_vl_vlmax : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL)
                        == `UDB_MXLEN'(get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)))
                        iff (ins.trap == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0) {
        bins target = {1'b1};
    }

    slideOffsets_zero : coverpoint ins.current.rs1_val == 0 {
        bins target = {1'b1};
    }

    slideOffsets_one : coverpoint ins.current.rs1_val == 1 {
        bins target = {1'b1};
    }

    slideOffsets_two : coverpoint ins.current.rs1_val == 2 {
        bins target = {1'b1};
    }

    slideOffsets_vlmaxd2 : coverpoint ins.current.rs1_val == `UDB_MXLEN'(get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE) / 2) {
        bins target = {1'b1};
    }

    slideOffsets_vlmaxm1 : coverpoint ins.current.rs1_val == `UDB_MXLEN'(get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE) - 1) {
        bins target = {1'b1};
    }

    slideOffsets_vlmax : coverpoint ins.current.rs1_val == `UDB_MXLEN'(get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }

    cp_custom_slideOffsets_zero    : cross slideOffsets_vl_vlmax, slideOffsets_zero;
    cp_custom_slideOffsets_one     : cross slideOffsets_vl_vlmax, slideOffsets_one;
    cp_custom_slideOffsets_two     : cross slideOffsets_vl_vlmax, slideOffsets_two;
    cp_custom_slideOffsets_vlmaxd2 : cross slideOffsets_vl_vlmax, slideOffsets_vlmaxd2;
    cp_custom_slideOffsets_vlmaxm1 : cross slideOffsets_vl_vlmax, slideOffsets_vlmaxm1;
    cp_custom_slideOffsets_vlmax   : cross slideOffsets_vl_vlmax, slideOffsets_vlmax;

    //// end cp_custom_slideOffsets////////////////////////////////////////////////
