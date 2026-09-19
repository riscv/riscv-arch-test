    cp_csr_fflags_voun : coverpoint {
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags")[4:0],
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")[4:0]
    } iff (ins.trap == 0 )  {
        // Value of FCSR.fflags
        wildcard bins NV   = {10'b0????_1????};
        wildcard bins NV1  = {10'b1????_1????};
        wildcard bins OF   = {10'b??0??_??1??};
        wildcard bins OF1  = {10'b??1??_??1??};
        wildcard bins UF   = {10'b???0?_???1?};
        wildcard bins UF1  = {10'b???1?_???1?};
        wildcard bins NX   = {10'b????0_????1};
        wildcard bins NX1  = {10'b????1_????1};
    }
