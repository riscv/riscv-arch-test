    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfncvt_rup_overflow_bf16
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // SEW = 16 (destination is 32-bit single, source is 64-bit double)
    vtype_sew_16: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e16 = {1};
    }

    // Rounding mode = RUP (round up, frm=3) (sample after to bypass sail issues)
    frm_rup: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "frm") {
        bins rup = {3};
    }

    // Overflow flag set after execution (fflags bit 2 = OF)
    fflags_of: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[2] {
        bins overflow = {1'b1};
    }

    cp_custom_vfncvt_rup_overflow: cross std_vec, vtype_sew_16, frm_rup, fflags_of;

//// end cp_custom_vfncvt_rup_overflow_bf16 ///////////////////////////////////////////////////////////////////////////
