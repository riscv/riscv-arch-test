    //////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_indexed
    //////////////////////////////////////////////////////////////////////////////////

    // Records that an indexed vector load/store was executed under otherwise-legal
    // conditions (vill=0, vstart=0, vl>0, mstatus.vs!=0, rs1 aligned to 8 bytes so
    // no element is misaligned for any supported SEW). Because every other
    // precondition is valid, any trap observed for this instruction is attributable
    // to MAXINDEXEEW gating the index EEW.

    cp_exceptionsv_indexed : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") != 0 &
                        ins.current.rs1_val[2:0] == 3'b000
                    }
    {
        bins true = {1'b1};
    }

    //// end cp_exceptionsv_indexed //////////////////////////////////////////////
