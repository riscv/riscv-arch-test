    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfncvt_rup_overflow
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Rounding mode = RUP (round up, frm=3)
    frm_rup: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_FCSR, "frm") {
        bins rup = {3};
    }

    // Overflow flag set after execution (fflags bit 2 = OF)
    fflags_of: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_FCSR, "fflags")[2] {
        bins overflow = {1'b1};
    }

    cp_custom_vfncvt_rup_overflow: cross std_vec, frm_rup, fflags_of;

//// end cp_custom_vfncvt_rup_overflow ///////////////////////////////////////////////////////////////////////////
