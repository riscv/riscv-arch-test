// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_wholereg_misaligned
// //////////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Exercise whole-register vector load/store (vl<nf>r / vs<nf>r) instructions
// whose base address is not naturally aligned to max(EEW/8, SEWMIN/8).
// Implementations are permitted to raise a misaligned-address exception on
// such accesses or to complete them successfully; both outcomes are valid.
// This coverpoint samples occurrence of the misaligned base with a valid
// vtype and is intended to be applied to the whole-register L/S instruction
// list.

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    vtype_valid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }

    // Non-zero low bits of the base address indicate misalignment relative to
    // any supported EEW of 2 bytes or larger.
    base_misalign : coverpoint ins.current.rs1_val[2:0] {
        bins offsets[] = {[3'b001:3'b111]};
    }

    cp_ssstrictv_ls_wholereg_misaligned : cross vtype_valid, base_misalign;

//// end cp_ssstrictv_ls_wholereg_misaligned ///////////////////////////////////////////////////////////////////
