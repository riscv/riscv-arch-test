function void ARCH_sample(int hart, int issue, ins_t ins);
    // Want to sample only if the SEW matches the target SEW of the file, some tests require
    // testing when vill is set, if vill=1 all other vtype bits are set to 0 so there is no
    // associated sew with these tests
    if (get_csr_val(hart, issue, `SAMPLE_BEFORE, "vtype", "vsew") == EFFVSEW ||
        get_csr_val(hart, issue, `SAMPLE_BEFORE, "vtype", "vill") == 1) begin
        case (traceDataQ[hart][issue][0].inst_name)
