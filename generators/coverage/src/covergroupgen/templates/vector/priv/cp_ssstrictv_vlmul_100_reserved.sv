// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vlmul_100_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Verify that vsetvli/vsetivli requesting vlmul=3'b100 (reserved) causes vill to be set

    vlmul_100_requested: coverpoint ins.current.insn[22:20] {
        bins reserved = {3'b100};
    }

    vill_set_after: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vtype", "vill") {
        bins set = {1};
    }

    cp_ssstrictv_vlmul_100_reserved: cross vlmul_100_requested, vill_set_after;

//// end cp_ssstrictv_vlmul_100_reserved ///////////////////////////////////////////////////////////////////
