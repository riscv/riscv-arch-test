// SPDX-License-Identifier: Apache-2.0

    zilx_loadops: coverpoint ins.current.insn {
        `include "general/RISCV_coverage_zilx_loads.svh"
    }
    zilx_rd_zero: coverpoint ins.current.insn[11:7] {
        bins zero = {5'b00000};
    }
    zilx_load_fault: coverpoint (
        `ifdef S_SUPPORTED
            ins.current.csr_wb[CSR_SCAUSE] ?
                get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCAUSE, "code") :
        `endif
        get_csr_field(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MCAUSE, "code")
    ) iff (ins.trap) {
        bins misaligned = {LOAD_ADDRESS_MISALIGNED};
        bins access_fault = {LOAD_ACCESS_FAULT};
    }
