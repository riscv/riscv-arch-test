function void @ARCH@_sample(int hart, int issue, ins_t ins);
    string inst_name = traceDataQ[hart][issue][0].inst_name;

    // Want to sample only if the SEW matches the target SEW of the file, some tests require
    // testing when vill is set, if vill=1 all other vtype bits are set to 0 so there is no
    // associated sew with these tests
    if (get_csr_field(hart, issue, `SAMPLE_BEFORE, CSR_VTYPE, "vsew") == @EFFVSEW@ ||
        get_csr_field(hart, issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 1) begin
        case (inst_name)
