// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcsr_reserved_bits
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Verify vcsr reserved bits [XLEN-1:3] read back as zero after CSR write with non-zero upper bits

    csrw_vcsr: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b000000001111_?????_001_?????_1110011};
        wildcard bins csrrs = {32'b000000001111_?????_010_?????_1110011};
        wildcard bins csrrc = {32'b000000001111_?????_011_?????_1110011};
    }

    rs1_upper_bits_nonzero: coverpoint (ins.current.rs1_val[`XLEN-1:3] != 0) {
        bins nonzero = {1'b1};
    }

    vcsr_upper_bits_zero_after: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vcsr", "vcsr")[`XLEN-1:3] {
        bins zero = {0};
    }

    cp_ssstrictv_vcsr_reserved_bits: cross csrw_vcsr, rs1_upper_bits_nonzero, vcsr_upper_bits_zero_after;

//// end cp_ssstrictv_vcsr_reserved_bits ///////////////////////////////////////////////////////////
