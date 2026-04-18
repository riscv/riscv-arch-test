    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_set
    // Universal flag-set check: every flag-setting FP instruction can raise NV
    // (sNaN input). DZ/NX/OF/UF are covered by per-instruction specific columns.
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    cp_csr_fflags_vdoun_set : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
    }

    cp_custom_vfp_flags_set : cross std_vec, cp_csr_fflags_vdoun_set;
`else
    `ifdef FLEN64
    cp_csr_fflags_vdoun_set : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
    }

    cp_custom_vfp_flags_set : cross std_vec, cp_csr_fflags_vdoun_set;
    `endif
`endif

    //// end cp_custom_vfp_flags_set////////////////////////////////////////////////
