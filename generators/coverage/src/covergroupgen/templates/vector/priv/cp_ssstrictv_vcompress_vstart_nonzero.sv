// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcompress_vstart_nonzero
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vcompress with non-zero vstart must raise illegal instruction exception
    vstart_nonzero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") {
        bins nonzero = {[1:$]};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    vcompress_funct6: coverpoint ins.current.insn[31:26] {
        bins vcompress = {6'b010111};
    }

    vcompress_funct3: coverpoint ins.current.insn[14:12] {
        bins opmvv = {3'b010};
    }

    cp_ssstrictv_vcompress_vstart_nonzero: cross vstart_nonzero, trap_occurred, vcompress_funct6, vcompress_funct3;

//// end cp_ssstrictv_vcompress_vstart_nonzero ///////////////////////////////////////////////////////////////
