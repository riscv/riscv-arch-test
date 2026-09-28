    cp_cntr : coverpoint ins.current.insn[31:20] iff (ins.get_gpr_reg(ins.current.rs1) == x0) {
        bins csr_cycle   = {CSR_CYCLE};
        bins csr_time    = {CSR_TIME};
        bins csr_instret = {CSR_INSTRET};
        `ifdef UDB_MXLEN_32
                bins csr_cycleh   = {CSR_CYCLEH};
                bins csr_timeh    = {CSR_TIMEH};
                bins csr_instreth = {CSR_INSTRETH};
        `endif
    }
