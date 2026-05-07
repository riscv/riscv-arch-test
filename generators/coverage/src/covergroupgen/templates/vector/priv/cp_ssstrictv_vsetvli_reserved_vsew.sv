// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vsetvli_reserved_vsew
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Reserved vsew encodings (vsew[2:0] = 1xx) in vsetvli/vsetivli immediate
    reserved_vsew: coverpoint ins.current.insn[25:23] {
        bins sew_100 = {3'b100};
        bins sew_101 = {3'b101};
        bins sew_110 = {3'b110};
        bins sew_111 = {3'b111};
    }

    vill_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vtype", "vill") {
        bins set = {1'b1};
    }

    cp_ssstrictv_vsetvli_reserved_vsew: cross reserved_vsew, vill_set;

//// end cp_ssstrictv_vsetvli_reserved_vsew /////////////////////////////////////////////////////////////////
