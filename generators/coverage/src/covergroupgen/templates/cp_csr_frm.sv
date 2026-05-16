    cp_csr_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm")  iff (ins.trap == 0 & ins.current.insn[14:12] == 3'b111)  {
        // Value of FCSR.frm during dynamic rounding
        bins rne  = {3'b000};
        bins rtz  = {3'b001};
        bins rdn  = {3'b010};
        bins rup  = {3'b011};
        bins rmm  = {3'b100};
        bins illegal  = default;
    }
