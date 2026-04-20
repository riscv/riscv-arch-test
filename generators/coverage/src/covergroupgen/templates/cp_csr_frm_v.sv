    cp_csr_frm_v : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm")  iff (ins.trap == 0 )  {
        // Value of FCSR.frm for vector FP instructions, which do not specify dynamic rounding mode in opcode
        bins rne  = {3'b000};
        bins rtz  = {3'b001};
        bins rdn  = {3'b010};
        bins rup  = {3'b011};
        bins rmm  = {3'b100};
        bins illegal  = default;
    }
