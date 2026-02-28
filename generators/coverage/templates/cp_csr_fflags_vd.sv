//////////////////////////////////////////////////////////////////////////////////
    // cp_csr_fflags_vd
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_fflags_vd : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        // Value of FCSR.fflags
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
        wildcard bins DZ   = (5'b?0??? => 5'b?1???);
        wildcard bins DZ1  = (5'b?1??? => 5'b?1???);
    }

    //// end cp_csr_fflags_vd////////////////////////////////////////////////
