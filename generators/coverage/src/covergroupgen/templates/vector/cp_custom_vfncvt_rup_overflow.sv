// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_custom_vfncvt_rup_overflow
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

`ifdef COVER_VFCUSTOM32
    // SEW = 32 (destination is 32-bit single, source is 64-bit double)
    vtype_sew_32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e32 = {2};
    }

    // Rounding mode = RUP (round up, frm=3)
    frm_rup: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm") {
        bins rup = {3};
    }

    // Overflow flag set after execution (fflags bit 2 = OF)
    fflags_of: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[2] {
        bins overflow = {1'b1};
    }

    cp_custom_vfncvt_rup_overflow: cross std_vec, vtype_sew_32, frm_rup, fflags_of;
`endif

//// end cp_custom_vfncvt_rup_overflow ///////////////////////////////////////////////////////////////////////////
