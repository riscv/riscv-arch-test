// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vsetvli_lmul_sew_ratio
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // All valid LMUL encodings from vsetvli immediate (insn[22:20] = zimm[2:0])
    requested_vlmul: coverpoint ins.current.insn[22:20] {
        bins mf8 = {3'b101};
        bins mf4 = {3'b110};
        bins mf2 = {3'b111};
        bins m1  = {3'b000};
        bins m2  = {3'b001};
        bins m4  = {3'b010};
        bins m8  = {3'b011};
        ignore_bins reserved = {3'b100};
    }

    // All valid SEW encodings from vsetvli immediate (insn[25:23] = zimm[5:3])
    requested_vsew: coverpoint ins.current.insn[25:23] {
        bins e8  = {3'b000};
        bins e16 = {3'b001};
        bins e32 = {3'b010};
        bins e64 = {3'b011};
        ignore_bins reserved[] = {[4:7]};
    }

    // vill must be set after execution (unsupported ratio)
    vill_set_after: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vtype", "vill") {
        bins set = {1'b1};
    }

    cp_ssstrictv_vsetvli_lmul_sew_ratio: cross requested_vlmul, requested_vsew, vill_set_after;

//// end cp_ssstrictv_vsetvli_lmul_sew_ratio //////////////////////////////////////////////////////////////
