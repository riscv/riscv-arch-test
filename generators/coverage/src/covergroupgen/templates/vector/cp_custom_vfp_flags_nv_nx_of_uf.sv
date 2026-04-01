    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_nv_nx_of_uf
    // For instructions that can raise NV, NX, OF, and UF but not DZ
    // with the standard test vectors: vfmul.vv, vfmul.vf.
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    cp_csr_fflags_vdoun_nv_nx_of_uf : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
        wildcard bins OF   = (5'b??0?? => 5'b??1??);
        wildcard bins OF1  = (5'b??1?? => 5'b??1??);
        wildcard bins UF   = (5'b???0? => 5'b???1?);
        wildcard bins UF1  = (5'b???1? => 5'b???1?);
        wildcard bins NX   = (5'b????0 => 5'b????1);
        wildcard bins NX1  = (5'b????1 => 5'b????1);
    }

    cp_custom_vfp_flags_nv_nx_of_uf : cross std_vec, cp_csr_fflags_vdoun_nv_nx_of_uf;
`else
    `ifdef FLEN64
    cp_csr_fflags_vdoun_nv_nx_of_uf : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") iff (ins.trap == 0 )  {
        wildcard bins NV   = (5'b0???? => 5'b1????);
        wildcard bins NV1  = (5'b1???? => 5'b1????);
        wildcard bins OF   = (5'b??0?? => 5'b??1??);
        wildcard bins OF1  = (5'b??1?? => 5'b??1??);
        wildcard bins UF   = (5'b???0? => 5'b???1?);
        wildcard bins UF1  = (5'b???1? => 5'b???1?);
        wildcard bins NX   = (5'b????0 => 5'b????1);
        wildcard bins NX1  = (5'b????1 => 5'b????1);
    }

    cp_custom_vfp_flags_nv_nx_of_uf : cross std_vec, cp_csr_fflags_vdoun_nv_nx_of_uf;
    `endif
`endif

    //// end cp_custom_vfp_flags_nv_nx_of_uf////////////////////////////////////////////////
