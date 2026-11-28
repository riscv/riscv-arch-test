    cp_cntr : coverpoint ins.current.insn[31:20] iff (ins.get_gpr_reg(ins.current.rs1) == x0) {
        `ifndef U_SUPPORTED
        bins csr_cycle   = {CSR_CYCLE};
        `elsif UDB_MCOUNTENABLE_EN_0
          `ifndef S_SUPPORTED
        bins csr_cycle   = {CSR_CYCLE};
          `elsif UDB_SCOUNTENABLE_EN_0
        bins csr_cycle   = {CSR_CYCLE};
          `endif
        `endif
        `ifndef U_SUPPORTED
        bins csr_time    = {CSR_TIME};
        `elsif UDB_MCOUNTENABLE_EN_1
          `ifndef S_SUPPORTED
        bins csr_time    = {CSR_TIME};
          `elsif UDB_SCOUNTENABLE_EN_1
        bins csr_time    = {CSR_TIME};
          `endif
        `endif
        `ifndef U_SUPPORTED
        bins csr_instret = {CSR_INSTRET};
        `elsif UDB_MCOUNTENABLE_EN_2
          `ifndef S_SUPPORTED
        bins csr_instret = {CSR_INSTRET};
          `elsif UDB_SCOUNTENABLE_EN_2
        bins csr_instret = {CSR_INSTRET};
          `endif
        `endif
        `ifdef UDB_MXLEN_32
                `ifndef U_SUPPORTED
                bins csr_cycleh   = {CSR_CYCLEH};
                `elsif UDB_MCOUNTENABLE_EN_0
                  `ifndef S_SUPPORTED
                bins csr_cycleh   = {CSR_CYCLEH};
                  `elsif UDB_SCOUNTENABLE_EN_0
                bins csr_cycleh   = {CSR_CYCLEH};
                  `endif
                `endif
                `ifndef U_SUPPORTED
                bins csr_timeh    = {CSR_TIMEH};
                `elsif UDB_MCOUNTENABLE_EN_1
                  `ifndef S_SUPPORTED
                bins csr_timeh    = {CSR_TIMEH};
                  `elsif UDB_SCOUNTENABLE_EN_1
                bins csr_timeh    = {CSR_TIMEH};
                  `endif
                `endif
                `ifndef U_SUPPORTED
                bins csr_instreth = {CSR_INSTRETH};
                `elsif UDB_MCOUNTENABLE_EN_2
                  `ifndef S_SUPPORTED
                bins csr_instreth = {CSR_INSTRETH};
                  `elsif UDB_SCOUNTENABLE_EN_2
                bins csr_instreth = {CSR_INSTRETH};
                  `endif
                `endif
        `endif
    }
