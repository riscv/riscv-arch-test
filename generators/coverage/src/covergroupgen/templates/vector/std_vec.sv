    std_vec: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) != 0 &
                        ins.trap == 0
                    }
    {
    bins true = {1'b1};
    }
