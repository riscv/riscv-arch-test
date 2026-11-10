    cp_csr_fflags_n : coverpoint {
        get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_FCSR, "fflags")[4:0],
        get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_FCSR, "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        // Value of FCSR.fflags
        wildcard bins NX   = {10'b????0_????1};
        wildcard bins NX1  = {10'b????1_????1};
    }
