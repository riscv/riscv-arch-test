    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_nv_nx_dz
    // For instructions that can raise NV, NX, and DZ but not OF/UF
    // with the standard test vectors: vfdiv.vv, vfdiv.vf, vfrdiv.vf, vfrec7.v.
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    cp_csr_fflags_vdoun_nv_nx_dz : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
        wildcard bins DZ   = (5'b?0??? => 5'b?1???);
        wildcard bins DZ1  = (5'b?1??? => 5'b?1???);
        wildcard bins NX   = (5'b????0 => 5'b????1);
        wildcard bins NX1  = (5'b????1 => 5'b????1);
    }

    cp_custom_vfp_flags_nv_nx_dz : cross std_vec, cp_csr_fflags_vdoun_nv_nx_dz;
`else
    `ifdef FLEN64
    cp_csr_fflags_vdoun_nv_nx_dz : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
        wildcard bins DZ   = (5'b?0??? => 5'b?1???);
        wildcard bins DZ1  = (5'b?1??? => 5'b?1???);
        wildcard bins NX   = (5'b????0 => 5'b????1);
        wildcard bins NX1  = (5'b????1 => 5'b????1);
    }

    cp_custom_vfp_flags_nv_nx_dz : cross std_vec, cp_csr_fflags_vdoun_nv_nx_dz;
    `endif
`endif

    //// end cp_custom_vfp_flags_nv_nx_dz////////////////////////////////////////////////
