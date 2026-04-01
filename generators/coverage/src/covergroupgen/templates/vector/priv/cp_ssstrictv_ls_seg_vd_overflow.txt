// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_ls_seg_vd_overflow
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `include "general/RISCV_coverage_standard_coverpoints_vector.svh"

    // Segment load/store where vd + NFIELDS > 32 (register numbers past 31)
    vd_nf_overflow : {coverpoint ins.current.insn[11:7],
                      coverpoint ins.current.insn[31:29]} {
        bins nf1_vd31 = {5'd31, 3'b001};  // NFIELDS=2, vd=31: 31+2=33 > 32
        bins nf2_vd30 = {5'd30, 3'b010};  // NFIELDS=3, vd=30: 30+3=33 > 32
        bins nf3_vd29 = {5'd29, 3'b011};  // NFIELDS=4, vd=29: 29+4=33 > 32
        bins nf4_vd28 = {5'd28, 3'b100};  // NFIELDS=5, vd=28: 28+5=33 > 32
        bins nf5_vd27 = {5'd27, 3'b101};  // NFIELDS=6, vd=27: 27+6=33 > 32
        bins nf6_vd26 = {5'd26, 3'b110};  // NFIELDS=7, vd=26: 26+7=33 > 32
        bins nf7_vd25 = {5'd25, 3'b111};  // NFIELDS=8, vd=25: 25+8=33 > 32
    }

    cp_ssstrictv_ls_seg_vd_overflow: cross std_trap_vec, vtype_sew_supported, vtype_lmul_1, vd_nf_overflow;

//// end cp_ssstrictv_ls_seg_vd_overflow ///////////////////////////////////////////////////////////
