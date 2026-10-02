    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_nv_nx_of
    // For instructions that can raise NV, NX, and OF but not DZ/UF
    // with the standard test vectors: vfadd.vv, vfadd.vf.
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    cp_csr_fflags_vdoun_nv_nx_of : coverpoint {
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0],
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        wildcard bins NV   = {10'b0????_1????};
        wildcard bins NV1  = {10'b1????_1????};
        wildcard bins OF   = {10'b??0??_??1??};
        wildcard bins OF1  = {10'b??1??_??1??};
        wildcard bins NX   = {10'b????0_????1};
        wildcard bins NX1  = {10'b????1_????1};
    }

    cp_custom_vfp_flags_nv_nx_of : cross std_vec, cp_csr_fflags_vdoun_nv_nx_of;
`else
    `ifdef D_SUPPORTED
    cp_csr_fflags_vdoun_nv_nx_of : coverpoint {
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0],
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        wildcard bins NV   = {10'b0????_1????};
        wildcard bins NV1  = {10'b1????_1????};
        wildcard bins OF   = {10'b??0??_??1??};
        wildcard bins OF1  = {10'b??1??_??1??};
        wildcard bins NX   = {10'b????0_????1};
        wildcard bins NX1  = {10'b????1_????1};
    }

    cp_custom_vfp_flags_nv_nx_of : cross std_vec, cp_csr_fflags_vdoun_nv_nx_of;
    `endif
`endif

    //// end cp_custom_vfp_flags_nv_nx_of////////////////////////////////////////////////
