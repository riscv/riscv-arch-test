function void ARCH_sample(int hart, int issue, ins_t ins);

    if (get_csr_val(hart, issue, `SAMPLE_BEFORE, "vtype", "vsew") == EFFVSEW ||
        get_csr_val(hart, issue, `SAMPLE_BEFORE, "vtype", "vill") == 1) begin
        case (traceDataQ[hart][issue][0].inst_name)
