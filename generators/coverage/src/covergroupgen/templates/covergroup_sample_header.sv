function void @ARCH@_sample(int hart, int issue, ins_t ins);
    string inst_name = traceDataQ[hart][issue][0].inst_name;

    case (inst_name)
