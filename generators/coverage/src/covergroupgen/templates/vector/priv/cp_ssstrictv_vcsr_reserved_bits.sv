// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcsr_reserved_bits
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Verify vcsr reserved bits [XLEN-1:3] read back as zero after CSR write with non-zero upper bits

    csrw_vcsr: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW} iff (ins.current.insn[31:20] == CSR_VCSR);
        wildcard bins csrrs = {CSRRS} iff (ins.current.insn[31:20] == CSR_VCSR);
        wildcard bins csrrc = {CSRRC} iff (ins.current.insn[31:20] == CSR_VCSR);
    }

    rs1_upper_bits_nonzero: coverpoint (ins.current.rs1_val[`UDB_MXLEN-1:3] != 0) {
        bins nonzero = {1'b1};
    }

    vcsr_upper_bits_zero_after: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vcsr", "vcsr")[`UDB_MXLEN-1:3] {
        bins zero = {0};
    }

    cp_ssstrictv_vcsr_reserved_bits: cross csrw_vcsr, rs1_upper_bits_nonzero, vcsr_upper_bits_zero_after;

//// end cp_ssstrictv_vcsr_reserved_bits ///////////////////////////////////////////////////////////
