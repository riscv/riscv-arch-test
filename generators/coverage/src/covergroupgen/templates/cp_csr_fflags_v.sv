    cp_csr_fflags_v : coverpoint {
        get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_FCSR, "fflags")[4:0],
        get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_FCSR, "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        // Value of FCSR.fflags
        wildcard bins NV   = {10'b0????_1????};
        wildcard bins NV1  = {10'b1????_1????};
    }
