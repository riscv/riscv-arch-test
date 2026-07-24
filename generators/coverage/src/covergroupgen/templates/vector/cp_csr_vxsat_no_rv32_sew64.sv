    //////////////////////////////////////////////////////////////////////////////////
    // cp_csr_vxsat_no_rv32_sew64
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vxsat : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vcsr", "vxsat")  iff (ins.trap == 0)  {
        // Value of VXSAT.vxsat (vector fixed-point saturation flag)
        bins zero = {1'b0};
        bins one  = {1'b1};

        `ifdef UDB_MXLEN_32
            `ifdef COVER_VX64
                ignore_bins ignore_one = { 1'b1 };
            `endif
        `endif
    }

    //// end cp_csr_vxsat_no_rv32_sew64 ////////////////////////////////////////////////
