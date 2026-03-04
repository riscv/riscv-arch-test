    vstart_csr: coverpoint ins.current.insn[31:20] {
        bins vstart = {12'h008};
    }

    csr_write: coverpoint ins.current.insn {
        wildcard bins csrrw     = {32'b????????????_?????_001_?????_1110011};
    }

    cp_exceptionsv_vstart_nonzero : cross
