    cp_cntr : coverpoint ins.current.insn[31:20] iff (ins.get_gpr_reg(ins.current.rs1) == x0) {
        bins csr_cycle   = {12'hC00};
        `ifdef TIME_CSR_IMPLEMENTED
                bins csr_time    = {12'hC01};
        `endif
        bins csr_instret = {12'hC02};
        `ifdef XLEN32
                bins csr_cycleh   = {12'hC80};
                `ifdef TIME_CSR_IMPLEMENTED
                        bins csr_timeh    = {12'hC81};
                `endif
                bins csr_instreth = {12'hC82};
        `endif
    }
