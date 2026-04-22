// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_element_misaligned
// //////////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Exercise vector memory accesses whose base address is not naturally aligned
// to the element size. The rule permits either a successful transfer or an
// address-misaligned exception on the offending element; both outcomes are
// architecturally valid, so this coverpoint samples only the occurrence of a
// misaligned base with a valid vtype.

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    vtype_valid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }

    // Non-zero low bits of the base address indicate misalignment relative to
    // elements of width >= 2 bytes. All seven non-aligned offsets are covered.
    base_misalign : coverpoint ins.current.rs1_val[2:0] {
        bins offsets[] = {[3'b001:3'b111]};
    }

    cp_ssstrictv_ls_element_misaligned : cross vtype_valid, base_misalign;

//// end cp_ssstrictv_ls_element_misaligned ///////////////////////////////////////////////////////////////////
