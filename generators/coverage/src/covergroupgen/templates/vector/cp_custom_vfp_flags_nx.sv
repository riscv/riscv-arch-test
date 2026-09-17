    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfp_flags_nx
    // For instructions that can raise NX but not NV/DZ/OF/UF
    // with the standard test vectors: int→float conversions
    // (vfcvt.f.x.v, vfcvt.f.xu.v, vfwcvt.f.x.v, vfwcvt.f.xu.v,
    //  vfncvt.f.x.w, vfncvt.f.xu.w).
    // Integer inputs cannot be sNaN so NV never fires.
    //////////////////////////////////////////////////////////////////////////////////

`ifndef COVER_VFCUSTOM64
    cp_csr_fflags_vdoun_nx : coverpoint {
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0],
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        wildcard bins NX   = {10'b????0_????1};
        wildcard bins NX1  = {10'b????1_????1};
    }

    cp_custom_vfp_flags_nx : cross std_vec, cp_csr_fflags_vdoun_nx;
`else
    `ifdef D_SUPPORTED
    cp_csr_fflags_vdoun_nx : coverpoint {
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0],
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        wildcard bins NX   = {10'b????0_????1};
        wildcard bins NX1  = {10'b????1_????1};
    }

    cp_custom_vfp_flags_nx : cross std_vec, cp_csr_fflags_vdoun_nx;
    `endif
`endif

    //// end cp_custom_vfp_flags_nx////////////////////////////////////////////////
