// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_custom_vfncvt_rup_overflow
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Narrowing word-to-half with round-up: confirm overflow is recognized in fflags
    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    // SEW = 32 (source is 32-bit word, narrowing dest is 16-bit half)
    vtype_sew_32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        bins e32 = {2};
    }

    // Rounding mode = RUP (round up, frm=3)
    frm_rup: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm") {
        bins rup = {3};
    }

    // Overflow flag set after execution (fflags bit 2 = OF)
    fflags_of: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[2] {
        bins overflow = {1'b1};
    }

    cp_custom_vfncvt_rup_overflow: cross std_vec, vtype_sew_32, frm_rup, fflags_of;

//// end cp_custom_vfncvt_rup_overflow ///////////////////////////////////////////////////////////////////////////
