function void ARCH_sample(int hart, int issue, ins_t ins);

    if (get_csr_val(hart, issue, `SAMPLE_BEFORE, "vtype", "vsew") == EFFVSEW) begin
        case (traceDataQ[hart][issue][0].inst_name)
