    cp_custom_fflags_accrue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags")  iff (ins.trap == 0 )  {
        // fflags accrues: this operation raises only NV, so any other set flag was carried in
        bins accrue_NX  = {5'b10001};
        bins accrue_UF  = {5'b10010};
        bins accrue_OF  = {5'b10100};
        bins accrue_DZ  = {5'b11000};
        bins accrue_all = {5'b11111};
    }
