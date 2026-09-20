    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_set
    // Universal flag-set check: every flag-setting FP instruction can raise NV
    // (sNaN input). DZ/NX/OF/UF are covered by per-instruction specific columns.
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    cp_csr_fflags_vdoun_set : coverpoint {
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0],
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        wildcard bins NV   = {10'b0????_1????};
        wildcard bins NV1  = {10'b1????_1????};
    }

    cp_custom_vfp_flags_set : cross std_vec, cp_csr_fflags_vdoun_set;
`else
    `ifdef D_SUPPORTED
    cp_csr_fflags_vdoun_set : coverpoint {
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0],
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        wildcard bins NV   = {10'b0????_1????};
        wildcard bins NV1  = {10'b1????_1????};
    }

    cp_custom_vfp_flags_set : cross std_vec, cp_csr_fflags_vdoun_set;
    `endif
`endif

    //// end cp_custom_vfp_flags_set////////////////////////////////////////////////
