// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vsetvli_x0_x0_reserved
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // vsetvli with rs1=x0 and rd=x0: reserved if vill was set or if new SEW/LMUL changes VLMAX
    rd_x0: coverpoint ins.current.insn[11:7] {
        bins zero = {5'b00000};
    }

    rs1_x0: coverpoint ins.current.insn[19:15] {
        bins zero = {5'b00000};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    // Case 1: vill was already set beforehand
    cp_ssstrictv_vsetvli_x0_x0_vill: cross rd_x0, rs1_x0, vtype_prev_vill_set, trap_occurred;

    // Case 2: new SEW/LMUL would change VLMAX (vill=0, new vsew or vlmul differs from current)
    new_sew_differs: coverpoint (ins.current.insn[25:23] !=
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")) {
        bins differs = {1'b1};
    }

    new_lmul_differs: coverpoint (ins.current.insn[22:20] !=
                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")) {
        bins differs = {1'b1};
    }

    cp_ssstrictv_vsetvli_x0_x0_vlmax_sew: cross rd_x0, rs1_x0, vtype_prev_vill_clear, new_sew_differs, trap_occurred;

    cp_ssstrictv_vsetvli_x0_x0_vlmax_lmul: cross rd_x0, rs1_x0, vtype_prev_vill_clear, new_lmul_differs, trap_occurred;

//// end cp_ssstrictv_vsetvli_x0_x0_reserved /////////////////////////////////////////////////////////
